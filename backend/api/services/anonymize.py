"""退会・管理者のユーザー削除

view から呼ぶ業務ロジック。退会（DELETE /users/me）と管理者のユーザー削除（DELETE /admin/users/:userId）で同じものを使う。

実装済み:
  - active_transactions(user): 進行中の取引の一覧（表示用の文言のリスト）。空なら退会できる
      購入者として: 支払い待ちの注文／未発送・キャンセル申請中の箱がある支払い済みの注文／
                    今後の確定済みの体験予約／応募済み・選考中の求人応募
      生産者として: 自分宛ての未発送・キャンセル申請中の箱（支払い済みの注文）／自分の体験の今後の確定済み予約／
                    自分の求人の応募済み・選考中の応募
  - anonymize_user(user): 個人情報を匿名化する（呼び出し側のトランザクションの中で使う）
      email を deleted_{id}@invalid、氏名を「退会ユーザー」、phone・birth_date・profile_image・prefecture を空、
      interests を空の配列、パスワードを使えない値、is_active=False、deleted_at=現在
      addresses・cart_items・favorite_products・favorite_producers を削除。生産者なら publish_status=suspended
      注文・予約・応募・レビュー・メッセージ・規約への同意履歴は残す
      パスワードを使えない値にするので、ほかの端末のセッションも自動でログアウトになる（Django の標準の仕組み）

使う場所:
  - DELETE /users/me（api/views/public/users.py）
  - DELETE /admin/users/:userId（管理者のステップで追加）
"""
from django.utils import timezone

from marche.models import (
    CartItem,
    FavoriteProducer,
    FavoriteProduct,
    JobApplication,
    Order,
    OrderShipment,
    Producer,
    PublishStatus,
    Reservation,
)

DELETED_NAME = "退会ユーザー"
OPEN_SHIPMENT = [OrderShipment.Status.UNSHIPPED, OrderShipment.Status.CANCEL_REQUESTED]
OPEN_APPLICATION = [JobApplication.Status.APPLIED, JobApplication.Status.SCREENING]


def active_transactions(user):
    """進行中の取引の文言のリスト（なければ空のリスト）"""
    now = timezone.now()
    found = []
    if Order.objects.filter(user=user, payment_status=Order.PaymentStatus.PENDING).exists():
        found.append("お支払い待ちの注文")
    if OrderShipment.objects.filter(order__user=user, order__payment_status=Order.PaymentStatus.PAID,
                                    status__in=OPEN_SHIPMENT).exists():
        found.append("発送前・キャンセル申請中の注文")
    if Reservation.objects.filter(user=user, status=Reservation.Status.CONFIRMED, slot__start_at__gt=now).exists():
        found.append("これからの体験予約")
    if JobApplication.objects.filter(user=user, status__in=OPEN_APPLICATION).exists():
        found.append("選考中の求人応募")

    producer = Producer.objects.filter(user=user).first()
    if producer is not None:
        if OrderShipment.objects.filter(producer=producer, order__payment_status=Order.PaymentStatus.PAID,
                                        status__in=OPEN_SHIPMENT).exists():
            found.append("生産者として発送前・キャンセル申請中の注文")
        if Reservation.objects.filter(slot__experience__producer=producer, status=Reservation.Status.CONFIRMED,
                                      slot__start_at__gt=now).exists():
            found.append("あなたの体験のこれからの予約")
        if JobApplication.objects.filter(job__producer=producer, status__in=OPEN_APPLICATION).exists():
            found.append("あなたの求人への選考中の応募")
    return found


def anonymize_user(user):
    """個人情報を匿名化する。呼び出し側でトランザクションを張り、先に本人へメールを送っておく"""
    now = timezone.now()
    user.email = f"deleted_{user.pk}@invalid"
    user.last_name = DELETED_NAME
    user.first_name = ""
    user.phone = None
    user.birth_date = None
    user.profile_image = None
    user.prefecture = None
    user.interests = []
    user.set_unusable_password()
    user.is_active = False
    user.deleted_at = now
    user.save()

    user.addresses.all().delete()
    CartItem.objects.filter(user=user).delete()
    FavoriteProduct.objects.filter(user=user).delete()
    FavoriteProducer.objects.filter(user=user).delete()
    Producer.objects.filter(user=user).update(publish_status=PublishStatus.SUSPENDED, updated_at=now)
