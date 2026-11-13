"""開発用：注文を支払い済みにする

使い方: docker compose exec backend python manage.py mark_order_paid TM-20261110-123456
仕様: api-spec.md「7. 実装で決めたこと」ステップ6a

Stripe のアカウント・キーがなくても、注文後の画面（生産者の注文管理・注文履歴など）を試せるようにするためのもの。
Webhook で支払いを受け取ったときと同じ処理（services/orders.py の mark_paid）をする:
pending → paid、購入者に注文確定メール（ゲストは閲覧用のURLつき）、生産者ごとに新規注文の通知・メール。
DEBUG のときだけ動く（本番では使えない）。
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.services import orders
from marche.models import Order


class Command(BaseCommand):
    help = "【開発用】注文を支払い済み（paid）にする。DEBUG のときだけ使える"

    def add_arguments(self, parser):
        parser.add_argument("order_no", help="注文番号（例: TM-20261110-123456）")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("このコマンドは開発環境（DEBUG=True）でだけ使えます。")
        order = Order.objects.filter(order_no=options["order_no"]).first()
        if order is None:
            raise CommandError(f"注文が見つかりません: {options['order_no']}")
        if not orders.mark_paid(order.id):
            raise CommandError(f"支払い待ち（pending）の注文ではありません（いまの状態: {order.payment_status}）")
        self.stdout.write(self.style.SUCCESS(f"{order.order_no} を支払い済みにしました"))
