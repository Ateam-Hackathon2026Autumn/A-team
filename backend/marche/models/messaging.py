"""メッセージ（見た目はチャット、中身はメール型の非同期）・通知・通知設定"""
from django.conf import settings
from django.db import models

from .base import TimeStampedModel


class MessageThread(TimeStampedModel):
    """メッセージスレッド

    生産者と会員のやり取り1件分。producer_id + user_id でユニーク。応募前の「事業者に質問する」も同じスレッドを使う。どの応募の話かは、スレッドの画面にこの会員の応募一覧（job_applications を JOIN）を並べて見せる。画面上の呼び方は「チャット」。"""

    producer = models.ForeignKey(
        "marche.Producer",
        on_delete=models.PROTECT,
        related_name="message_threads",
        verbose_name="生産者",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="message_threads",
        verbose_name="相手の会員",
    )

    # 最後のメッセージ日時。一覧の並び順。メッセージ送信時に一緒に更新
    last_message_at = models.DateTimeField(
        verbose_name="最後のメッセージ日時",
    )

    class Meta:
        db_table = "message_threads"
        verbose_name = "メッセージスレッド"
        verbose_name_plural = "メッセージスレッド"
        constraints = [
            models.UniqueConstraint(fields=['producer', 'user'], name="uniq_message_threads_producer_user"),
        ]


class Message(TimeStampedModel):
    """メッセージ

    リアルタイム通信は使わないメール型のやり取り。送信時に、相手がこのスレッドに未読（read_at が空）のメッセージを持っていなければ「新しいメッセージが届きました」と通知メールを1通送る（相手の notification_settings.email_message がオンのとき）。本文はサイトのチャット画面で読む。新着メッセージは notifications に入れず、未読件数は messages の read_at から数える。"""

    thread = models.ForeignKey(
        "marche.MessageThread",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="スレッド",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="messages",
        verbose_name="送信者",
    )

    body = models.TextField(
        verbose_name="本文",
    )

    # 添付ファイル（S3のキー）
    attachment = models.FileField(
        upload_to="messages/",
        max_length=500,
        null=True,
        blank=True,
        verbose_name="添付ファイル",
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="相手が読んだ日時",
    )

    class Meta:
        db_table = "messages"
        verbose_name = "メッセージ"
        verbose_name_plural = "メッセージ"


class Notification(TimeStampedModel):
    """通知

    個人宛てのサイト内通知。注文・発送・キャンセル・応募結果・予約などの各処理の中で、メール送信と同時に登録する（設定で止められない）。新着メッセージは入れない。インデックスは (user_id, created_at)（一覧を新しい順に取る）と (user_id, read_at)（未読件数を数える）。link_path は画面のパスなので、画面のURL構成を変えると古い通知のリンクが切れる点に注意。"""

    class NotificationType(models.TextChoices):
        NEW_ORDER = "new_order", "新規注文"
        SHIPPED = "shipped", "発送"
        CANCEL_REQUESTED = "cancel_requested", "キャンセル申請"
        CANCELED = "canceled", "キャンセル確定・返金"
        APPLICATION_RESULT = "application_result", "応募結果"
        RESERVATION = "reservation", "体験予約"

    # 通知を受け取る会員（生産者も含む）。ゲストには作らない
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="通知を受け取る会員",
    )

    # new_order（新規注文）/ shipped（発送）/ cancel_requested（キャンセル申請）/ canceled（キャンセル確定・返金）/ application_result（応募結果）/ reservation（体験予約）
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name="通知の種類",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    body = models.TextField(
        null=True,
        blank=True,
        verbose_name="本文",
    )

    # 押したときに開く画面のパス（例：/dashboard/orders/123）（S3のキー）    
    link_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="押したときに開く画面のパス",
    )

    # 既読日時。未読なら空
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="既読日時",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "通知"
        verbose_name_plural = "通知"
        indexes = [
            models.Index(fields=['user', 'created_at'], name="idx_notifications_user_created"),
            models.Index(fields=['user', 'read_at'], name="idx_notifications_user_read"),
        ]

    def __str__(self):
        return self.title


class NotificationSetting(TimeStampedModel):
    """通知設定

    設定で止められるのは、届かなくても取引に困らないメールだけ。注文確認・発送・キャンセル確定・返金・応募結果・予約確定のメールと、サイト内の通知（notifications）は設定に関係なく必ず送る。"""

    # 会員。1人につき1行（会員登録時に作る）
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_settings",
        verbose_name="会員",
    )

    # 新着メッセージをメールで受け取る（初期値 True）
    email_message = models.BooleanField(
        default=True,
        verbose_name="新着メッセージをメールで受け取る",
    )

    # お気に入り生産者の新着をメールで受け取る（初期値 True）。favorite_producers.notify と両方オンのときだけ送る
    email_favorite = models.BooleanField(
        default=True,
        verbose_name="お気に入り生産者の新着をメールで受け取る",
    )

    # 運営からのお知らせをメールで受け取る（初期値 True）
    email_news = models.BooleanField(
        default=True,
        verbose_name="運営からのお知らせをメールで受け取る",
    )

    # Push 通知を受け取る（初期値 False）。Push の送信と端末の登録は拡張
    push_enabled = models.BooleanField(
        default=False,
        verbose_name="Push 通知を受け取る",
    )

    class Meta:
        db_table = "notification_settings"
        verbose_name = "通知設定"
        verbose_name_plural = "通知設定"
