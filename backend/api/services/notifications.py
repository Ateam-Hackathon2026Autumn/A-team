"""サイト内の通知とメールをまとめて送る

- notify(): notifications に1行登録し、トランザクションが確定したらメールも送る
  - 処理がロールバックされたら、通知も消えてメールも送られない
  - メールの送信に失敗しても、処理自体は成功として扱う（mail.send がログに残す）
  - 退会・停止済み（is_active=False）の会員には何もしない
- notify_order_buyer(): 注文の購入者に知らせる。会員は notify()、ゲスト（orders.user が空）はメールだけ
  - ゲストへのメールにはトークン付きURLを載せられない（DB にはハッシュしかない）ので、
    「注文確認メールのURLからご確認ください」と案内する
- notification_type: new_order / shipped / cancel_requested / canceled / cancel_rejected / application_result / reservation

これから追加するもの:
  - チャットは notifications に入れない。相手がそのやり取りに未読を持っていないときだけメール
  - 止められるメール（メッセージ・お気に入りの新着・お知らせ）だけ notification_settings を見る

使う場所: 予約枠の中止・発送・キャンセルの承認と拒否・管理者キャンセル（実装済み）、注文・予約・応募結果などの各処理
"""
from django.db import transaction

from marche.models import Notification

from . import mail


def notify(user, notification_type, title, body, link_path=None):
    """通知を1件作り、同じ内容のメールを送る。作った Notification を返す（送らなかったら None）"""
    if not user.is_active:
        return None
    notification = Notification.objects.create(
        user=user, notification_type=notification_type, title=title, body=body, link_path=link_path,
    )
    greeting = f"{user.last_name} {user.first_name} 様\n\n"
    transaction.on_commit(lambda: mail.send(user.email, title, greeting + body))
    return notification


GUEST_ORDER_GUIDE = "ご注文の状況は、ご注文時にお送りした注文確認メールのURLからご確認いただけます。\n"


def notify_order_buyer(order, notification_type, title, body, link_path=None):
    """注文の購入者に知らせる。会員は通知＋メール、ゲストはメールだけ（Notification は作らないので None を返す）"""
    if order.user_id:
        return notify(order.user, notification_type, title, body, link_path)
    greeting = f"{order.guest_name or 'お客'} 様\n\n"
    transaction.on_commit(lambda: mail.send(order.guest_email, title, greeting + body + "\n" + GUEST_ORDER_GUIDE))
    return None
