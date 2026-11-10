"""体験の予約（申込・キャンセル）

view から呼ぶ業務ロジック。公開側の申込・キャンセルと、申込状況の表示で同じ判定を使う。

実装済み:
  - booking_deadline(slot, experience): 申込・キャンセルの締め切り日時（start_at − booking_deadline_hours）
  - is_bookable(slot, experience, now): 今申し込めるか（受付中・締め切り前・空きあり）
  - is_cancellable(reservation, now): 今キャンセルできるか（確定済み・締め切り前）
  - apply_for_experience(experience_id, user, data): 申込（1つのトランザクション）
      体験 → 日程の順にロック（生産者側の予約枠の更新と同じ順）→ 公開中か・日程がこの体験のものか（違えば 404）→
      受付中・締め切り前（409 BOOKING_CLOSED）→ 自分の体験（409 CANNOT_APPLY_OWN）→ 人数のルール（400）→
      合計金額（expectedTotalAmount と違えば 409 QUOTE_CHANGED）→ 同じ日程の予約（409 ALREADY_APPLIED）→
      定員（未就学児も含めた全員。409 CAPACITY_EXCEEDED）→ reservations（confirmed）を作り reserved_count を増やす
      申込者に予約確定の通知・メール、生産者に新しい予約の通知・メール
  - cancel_reservation(reservation_id, user): キャンセル。体験 → 日程 → 予約の順にロックし、確定済み・締め切り前のときだけ
      canceled にして reserved_count を減らす（できなければ 409 CANCEL_NOT_ALLOWED）。生産者に通知・メール

使う場所: api/views/public/experiences.py、api/serializers/public/experiences.py
"""
import secrets
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import serializers, status

from marche.models import Experience, ExperienceSlot, Notification, Reservation

from ..common.exceptions import ApiError, Conflict
from .notifications import MY_EXPERIENCES_PATH, notify
from .visibility import public_content

ACTIVE_STATUSES = [Reservation.Status.APPLIED, Reservation.Status.CONFIRMED, Reservation.Status.ATTENDED]
PRODUCER_EXPERIENCE_PATH = "/dashboard/experiences/{experience_id}/participants"


def booking_deadline(slot, experience):
    return slot.start_at - timedelta(hours=experience.booking_deadline_hours)


def is_bookable(slot, experience, now):
    return (slot.status == ExperienceSlot.Status.OPEN and booking_deadline(slot, experience) > now
            and slot.reserved_count < slot.capacity)


def is_cancellable(reservation, now):
    return (reservation.status == Reservation.Status.CONFIRMED
            and booking_deadline(reservation.slot, reservation.slot.experience) > now)


def experience_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "EXPERIENCE_NOT_FOUND", "体験が見つかりません。")


def generate_reservation_no():
    """予約番号 RV-YYYYMMDD-NNNNNN（日本時間の日付＋ランダム6桁）。重なったら作り直す"""
    today = timezone.localdate().strftime("%Y%m%d")
    for _ in range(10):
        reservation_no = f"RV-{today}-{secrets.randbelow(10 ** 6):06d}"
        if not Reservation.objects.filter(reservation_no=reservation_no).exists():
            return reservation_no
    raise RuntimeError("予約番号を作れませんでした")


def total_amount(experience, adult_count, child_count):
    """大人料金×大人＋子ども料金×子ども。未就学児は無料"""
    return experience.price_adult * adult_count + (experience.price_child or 0) * child_count


def apply_for_experience(experience_id, user, data):
    """申込を作って返す。data は ApplicationCreateSerializer の validated_data"""
    now = timezone.now()
    with transaction.atomic():
        experience = (Experience.objects.select_for_update().filter(pk=experience_id)
                      .select_related("producer__user").first())
        if experience is None or not public_content(Experience.objects.filter(pk=experience_id)).exists():
            raise experience_not_found()
        slot = ExperienceSlot.objects.select_for_update().filter(pk=data["slot_id"], experience=experience).first()
        if slot is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "SLOT_NOT_FOUND", "日程が見つかりません。")
        if slot.status != ExperienceSlot.Status.OPEN or booking_deadline(slot, experience) <= now:
            raise Conflict("BOOKING_CLOSED", "この日程の申込は締め切りました。")
        if experience.producer.user_id == user.pk:
            raise Conflict("CANNOT_APPLY_OWN", "ご自身の体験には申し込めません。")

        children = data["child_count"] + data["infant_count"]
        if data["child_count"] and experience.price_child is None:
            raise serializers.ValidationError({"child_count": ["この体験は子どもの申込を受け付けていません。"]})
        if children and not experience.family_ok:
            raise serializers.ValidationError({"child_count": ["この体験は大人だけで参加する体験です。"]})

        amount = total_amount(experience, data["adult_count"], data["child_count"])
        if amount != data["expected_total_amount"]:
            raise Conflict("QUOTE_CHANGED", "料金が変わりました。内容を確認してから、もう一度お申し込みください。")
        if Reservation.objects.filter(slot=slot, user=user, status__in=ACTIVE_STATUSES).exists():
            raise Conflict("ALREADY_APPLIED", "この日程にはすでに申し込んでいます。")
        people = data["adult_count"] + children
        if slot.reserved_count + people > slot.capacity:
            raise Conflict("CAPACITY_EXCEEDED",
                           f"空きが足りません（残り{max(slot.capacity - slot.reserved_count, 0)}名）。")

        reservation = Reservation.objects.create(
            reservation_no=generate_reservation_no(), slot=slot, user=user,
            adult_count=data["adult_count"], child_count=data["child_count"], infant_count=data["infant_count"],
            representative_name=f"{data['last_name']} {data['first_name']}", phone=data["phone"],
            message=data.get("message"), total_amount=amount, status=Reservation.Status.CONFIRMED,
            policy_agreed_at=now)
        ExperienceSlot.objects.filter(pk=slot.pk).update(reserved_count=F("reserved_count") + people, updated_at=now)
        _notify_applied(experience, slot, reservation, people)
    return reservation


def _when(slot):
    return timezone.localtime(slot.start_at).strftime("%Y年%m月%d日 %H:%M")


def _notify_applied(experience, slot, reservation, people):
    notify(reservation.user, Notification.NotificationType.RESERVATION, "体験の予約が確定しました",
           f"「{experience.title}」の予約が確定しました。\n\n"
           f"予約番号：{reservation.reservation_no}\n日時：{_when(slot)}〜（約{slot.duration_min}分）\n"
           f"場所：{experience.place}\n人数：{people}名\n"
           f"参加費：{reservation.total_amount:,}円（当日現地でお支払いください）\n\n"
           f"キャンセルは開催の{experience.booking_deadline_hours}時間前まで、マイページからできます。\n",
           MY_EXPERIENCES_PATH)
    notify(experience.producer.user, Notification.NotificationType.RESERVATION, "体験の予約が入りました",
           f"「{experience.title}」（{_when(slot)}〜）に予約が入りました。\n\n"
           f"予約番号：{reservation.reservation_no}\n代表者：{reservation.representative_name}\n人数：{people}名\n",
           PRODUCER_EXPERIENCE_PATH.format(experience_id=experience.id))


def cancel_reservation(reservation_id, user):
    """自分の予約をキャンセルして返す。他人・存在しない予約は 404 RESERVATION_NOT_FOUND"""
    now = timezone.now()
    with transaction.atomic():
        found = Reservation.objects.filter(pk=reservation_id, user=user).values("slot_id", "slot__experience_id").first()
        if found is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "RESERVATION_NOT_FOUND", "予約が見つかりません。")
        # 生産者側（予約枠の中止）と同じく、体験 → 日程 → 予約の順にロックする
        experience = (Experience.objects.select_for_update().select_related("producer__user")
                      .get(pk=found["slot__experience_id"]))
        slot = ExperienceSlot.objects.select_for_update().get(pk=found["slot_id"])
        reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
        slot.experience = experience
        reservation.slot = slot
        if not is_cancellable(reservation, now):
            raise Conflict("CANCEL_NOT_ALLOWED",
                           "キャンセルの受付期間が過ぎたか、キャンセルできない予約です。主催者にメッセージでご連絡ください。")
        reservation.status = Reservation.Status.CANCELED
        reservation.save(update_fields=["status", "updated_at"])
        people = reservation.adult_count + reservation.child_count + reservation.infant_count
        ExperienceSlot.objects.filter(pk=slot.pk).update(
            reserved_count=F("reserved_count") - people, updated_at=now)
        notify(experience.producer.user, Notification.NotificationType.RESERVATION, "体験の予約がキャンセルされました",
               f"「{experience.title}」（{_when(slot)}〜）の予約がキャンセルされました。\n\n"
               f"予約番号：{reservation.reservation_no}\n代表者：{reservation.representative_name}\n人数：{people}名\n",
               PRODUCER_EXPERIENCE_PATH.format(experience_id=experience.id))
    return reservation
