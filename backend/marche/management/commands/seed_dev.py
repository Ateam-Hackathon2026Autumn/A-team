"""開発用：画面の確認に使うデータをまとめて入れる

使い方:
    docker compose exec backend python manage.py seed_dev           # データを入れる
    docker compose exec backend python manage.py seed_dev --reset   # このコマンドのデータを消して入れ直す

- DEBUG のときだけ動く（本番では使えない）
- 何回実行しても増えない（開発用アカウントがもうあれば、何もしないで終わる）
- ほかのデータは消さない。--reset が消すのは、開発用アカウントとその人たちに紐づくデータだけ
- マスタ（カテゴリー・都道府県）も一緒に入れる（marche/fixtures/ の内容。もうある行はそのままにする）
- 画像は marche/seed_images/ の写真（product-01.jpg・producer-1-cover.jpg・experience-1.jpg など）を使う。
  その名前のファイルがなければ、色つきのダミー画像を作って代わりにする（保存先は開発では backend/media/）

入るデータ（パスワードは全員 DEV_PASSWORD）:
    会員     buyer1@example.com（注文・予約・応募・お気に入り・カートあり）
             buyer2@example.com（購入なし。体験の予約と求人の採用だけ）
             applicant@example.com（生産者申請が審査中）
    生産者   producer1@example.com 山本農園（農業・長野・公開中）
             producer2@example.com 海風水産（漁業・静岡・公開中・新規参加）
             producer3@example.com 牧ファーム（畜産・北海道・運営が掲載停止中）
    商品20件（公開中・下書き・非公開・掲載停止・在庫切れ・在庫管理なし・割引・冷蔵・冷凍・定期便・予約商品）
    体験5件（予約できる・満席・締め切り後・日程なし・下書き）
    求人5件（募集中・募集期間が終わった・採用枠がいっぱい・長期・下書き）
    注文10件（支払い待ち・未発送・発送済み・配達完了・キャンセル申請中・返金待ち・返金済み・ゲスト・決済失敗）
    レビュー10件（返信あり・なし。「安曇野ふじ」は3件）
"""
import hashlib
import io
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone
from PIL import Image, ImageDraw

from api.services.pricing import tax_amounts
from api.services.reviews import recalculate_rating
from marche.models import (Address, ApplicationWorkDate, Area, CartItem, Category, Experience, ExperienceImage,
                            ExperienceSlot, FavoriteProducer, FavoriteProduct, Job, JobApplication, JobWorkDate,
                            MessageThread, Order, OrderItem, OrderShipment, Prefecture, Producer, ProducerApplication,
                            ProducerImage, ProducerStory, Product, ProductImage, ProductReview, PublishStatus, Report,
                            Reservation, ShippingSetting, User, UserConsent, WagePayment)

DEV_PASSWORD = "MarcheDev#2026"
ORDER_PREFIX = "TM-SEED-"
RESERVATION_PREFIX = "RV-SEED-"
# 確認用の写真の置き場所（Git に入れる。ファイル名は product-01.jpg・producer-1-profile.jpg・experience-1.jpg など）
SEED_IMAGE_DIR = Path(__file__).resolve().parent.parent.parent / "seed_images"
FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

# (メール, 姓, 名, 電話, 都道府県ID)
MEMBERS = [
    ("buyer1@example.com", "佐藤", "花子", "09011110001", 13),
    ("buyer2@example.com", "鈴木", "大輔", "09011110002", 27),
    ("applicant@example.com", "高橋", "美咲", "09011110003", 40),
]
PRODUCER_USERS = [
    ("producer1@example.com", "山本", "健太", "09022220001", 20),
    ("producer2@example.com", "海野", "洋平", "09022220002", 22),
    ("producer3@example.com", "牧", "草太", "09022220003", 1),
]
SEED_EMAILS = [row[0] for row in MEMBERS + PRODUCER_USERS]

# 商品: (生産者, 名前, カテゴリー, 内容量, 価格, 温度帯, 色, そのほかの項目)
PRODUCTS = [
    (1, "安曇野ふじ 家庭用 5kg", "果物", "5kg", 5400, "normal", (200, 60, 60),
     dict(discount_rate=10, stock=12, accepts_delivery_date=True, method="葉とらず栽培")),
    (1, "シナノゴールド 3kg", "果物", "3kg", 3800, "normal", (225, 200, 80), dict(stock=8)),
    (1, "朝どれレタス 3玉", "野菜", "3玉", 1200, "chilled", (120, 200, 120), dict(stock=None)),
    (1, "完熟トマト 2kg", "野菜", "2kg", 2400, "chilled", (220, 70, 50), dict(stock=3)),
    (1, "季節の野菜セット", "野菜", "8〜10品", 3500, "normal", (90, 160, 90),
     dict(stock=20, is_subscription=True)),
    (1, "安曇野のコシヒカリ 5kg", "米", "5kg", 3900, "normal", (235, 225, 200), dict(stock=30, tax_rate=8)),
    (1, "りんごジュース 1L×3本", "加工品", "1L×3本", 3300, "normal", (230, 170, 60), dict(stock=0)),
    (1, "りんごのドライチップス", "加工品", "50g×3袋", 1500, "normal", (200, 140, 90), dict(discount_rate=20, stock=15)),
    (1, "新米の予約 10kg", "米", "10kg", 7200, "normal", (240, 235, 215), dict(stock=10, is_preorder=True)),
    (1, "試作中のりんごバター", "加工品", "150g", 900, "normal", (210, 150, 100),
     dict(stock=None, publish_status=PublishStatus.DRAFT, image=False)),
    (2, "沼津 あじの開き干し 10枚", "魚介類", "10枚", 3200, "chilled", (120, 160, 200), dict(stock=25)),
    (2, "金目鯛の煮付けセット", "魚介類", "2切れ×2", 4800, "frozen", (220, 90, 90), dict(discount_rate=15, stock=6)),
    (2, "釜揚げしらす 500g", "魚介類", "500g", 2600, "chilled", (235, 235, 240), dict(stock=2)),
    (2, "桜えびのかき揚げ 6枚", "加工品", "6枚", 2900, "frozen", (240, 150, 130), dict(stock=18)),
    (2, "さばのみりん干し 6枚", "魚介類", "6枚", 2200, "chilled", (150, 130, 100), dict(stock=0)),
    (2, "干物の詰め合わせ", "魚介類", "5種", 5500, "chilled", (100, 140, 180),
     dict(stock=9, accepts_delivery_date=True)),
    (2, "販売をやめた干物", "魚介類", "3枚", 1800, "chilled", (140, 140, 140),
     dict(stock=5, publish_status=PublishStatus.PRIVATE)),
    (2, "運営が掲載を止めた商品", "その他", "1個", 1000, "chilled", (170, 120, 170),
     dict(stock=5, publish_status=PublishStatus.SUSPENDED)),
    (3, "放牧牛のハンバーグ 6個", "肉", "150g×6", 4200, "frozen", (150, 90, 70), dict(stock=10)),
    (3, "手づくりソーセージ", "肉", "300g", 1900, "frozen", (190, 110, 90), dict(stock=10)),
]


def seed_image(names, color):
    """names の順に marche/seed_images/{名前}.jpg を探し、最初に見つかった写真を返す。なければ色つきのダミー画像"""
    for name in names:
        path = SEED_IMAGE_DIR / f"{name}.jpg"
        if path.is_file():
            return path.read_bytes()
    return dummy_image(color)


def dummy_image(color):
    """色つきのダミー画像（JPEG のバイト列）"""
    image = Image.new("RGB", (800, 600), color)
    draw = ImageDraw.Draw(image)
    light = tuple(min(255, c + 35) for c in color)
    draw.ellipse((250, 150, 550, 450), fill=light)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "【開発用】画面の確認に使うデータを入れる。DEBUG のときだけ使える"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="このコマンドが作ったアカウントと、その人たちのデータを消してから入れ直す")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("このコマンドは開発環境（DEBUG=True）でだけ使えます。")
        self.load_masters()

        exists = User.objects.filter(email__in=SEED_EMAILS).exists()
        if exists and not options["reset"]:
            self.stdout.write("開発用のデータはもう入っています（入れ直すときは --reset を付けてください）。")
            self.print_accounts()
            return
        with transaction.atomic():
            if exists:
                self.reset()
            self.seed()
        self.stdout.write(self.style.SUCCESS(
            f"開発用のデータを入れました：会員 {len(MEMBERS)}・生産者 {len(PRODUCER_USERS)}・"
            f"商品 {len(PRODUCTS)}・体験 5・求人 5・注文 10・レビュー 10"))
        self.print_accounts()

    def load_masters(self):
        """カテゴリー・エリア・都道府県のマスタを入れる（marche/fixtures/ の内容）

        loaddata は ID を決めて入れるので、同じ名前の行が別の ID でもうあると失敗する。
        ここでは名前（都道府県は ID）で探し、ない行だけを足す。何回実行しても増えない。
        """
        for record in json.loads((FIXTURE_DIR / "categories.json").read_text(encoding="utf-8")):
            fields = record["fields"]
            Category.objects.get_or_create(name=fields["name"], defaults={"sort_order": fields["sort_order"]})
        areas = {}  # フィクスチャーの中のエリアID → 実際の行
        for record in json.loads((FIXTURE_DIR / "prefectures.json").read_text(encoding="utf-8")):
            fields = record["fields"]
            if record["model"] == "marche.area":
                areas[record["pk"]], _ = Area.objects.get_or_create(
                    name=fields["name"], defaults={"sort_order": fields["sort_order"]})
            else:
                Prefecture.objects.get_or_create(
                    pk=record["pk"], defaults={"name": fields["name"], "area": areas[fields["area"]]})

    def print_accounts(self):
        self.stdout.write(f"ログイン用のアカウント（パスワードは全員 {DEV_PASSWORD}）:")
        for email, last_name, first_name, *_ in MEMBERS + PRODUCER_USERS:
            self.stdout.write(f"  {email}  {last_name} {first_name}")

    # ------------------------------------------------------------------
    # 消す（--reset）
    # ------------------------------------------------------------------
    def reset(self):
        """開発用アカウントと、その人たち（会員として・生産者として）に紐づくデータだけを消す"""
        users = User.objects.filter(email__in=SEED_EMAILS)
        producers = Producer.objects.filter(user__in=users)
        image_keys = self.seed_image_keys(users)
        try:
            ProductReview.objects.filter(Q(user__in=users) | Q(product__producer__in=producers)).delete()
            orders = Order.objects.filter(
                Q(order_no__startswith=ORDER_PREFIX) | Q(user__in=users) | Q(order_shipments__producer__in=producers))
            Order.objects.filter(pk__in=orders.values("pk")).delete()
            Reservation.objects.filter(Q(user__in=users) | Q(slot__experience__producer__in=producers)).delete()
            applications = JobApplication.objects.filter(Q(user__in=users) | Q(job__producer__in=producers))
            WagePayment.objects.filter(job_application__in=applications).delete()
            applications.delete()
            MessageThread.objects.filter(Q(user__in=users) | Q(producer__in=producers)).delete()
            Report.objects.filter(reporter__in=users).delete()
            Experience.objects.filter(producer__in=producers).delete()
            Job.objects.filter(producer__in=producers).delete()
            Product.objects.filter(producer__in=producers).delete()
            producers.delete()
            UserConsent.objects.filter(user__in=users).delete()
            users.delete()
        except ProtectedError as error:
            raise CommandError(f"ほかのデータから参照されているため消せませんでした: {error}")
        for key in image_keys:
            try:
                default_storage.delete(key)
            except Exception:  # 画像が消せなくてもデータの入れ直しは続ける
                pass
        self.stdout.write("前回の開発用のデータを消しました。")

    def seed_image_keys(self, users):
        """このコマンドが作った画像（images/{ユーザーID}/seed-…）のキー"""
        keys = []
        for user in users:
            prefix = f"images/{user.id}/"
            try:
                _, files = default_storage.listdir(prefix)
            except Exception:
                continue
            keys += [prefix + name for name in files if name.startswith("seed-")]
        return keys

    # ------------------------------------------------------------------
    # 入れる
    # ------------------------------------------------------------------
    def seed(self):
        now = timezone.now()
        today = timezone.localdate()
        self.image_count = 0

        def make_user(email, last_name, first_name, phone, prefecture_id):
            return User.objects.create_user(
                email=email, password=DEV_PASSWORD, last_name=last_name, first_name=first_name, phone=phone,
                birth_date="1988-04-01", prefecture_id=prefecture_id, interests=["vegetables", "experiences"],
                email_verified_at=now)

        buyer1, buyer2, applicant = [make_user(*row) for row in MEMBERS]
        user1, user2, user3 = [make_user(*row) for row in PRODUCER_USERS]

        # ---- 生産者 ----
        producer1 = self.make_producer(
            1, user1, "山本農園", Producer.Genre.AGRICULTURE, "安曇野市", "りんご・野菜・米",
            "北アルプスのふもとで、りんごと野菜を育てています。", (90, 140, 90),
            career_start_year=2012, founded_year=1975, accepts_experience=True, recruiting=True,
            approved_at=now - timedelta(days=200), featured_score=80)
        producer2 = self.make_producer(
            2, user2, "海風水産", Producer.Genre.FISHERY, "沼津市", "干物・しらす",
            "沼津港で水揚げした魚を、その日のうちに干物にしています。", (80, 130, 180),
            career_start_year=today.year - 1, founded_year=today.year - 1, accepts_experience=True, recruiting=False,
            approved_at=now - timedelta(days=10), featured_score=60)
        producer3 = self.make_producer(
            3, user3, "牧ファーム", Producer.Genre.LIVESTOCK, "帯広市", "牛肉・加工品",
            "十勝の放牧牛を育てています。", (150, 110, 80),
            career_start_year=2005, founded_year=2005, accepts_experience=False, recruiting=False,
            approved_at=now - timedelta(days=400), publish_status=PublishStatus.SUSPENDED)
        producers = {1: producer1, 2: producer2, 3: producer3}

        settings_by_producer = {
            1: {"normal": self.shipping(producer1, "normal", 900, 8000, "2〜4日で発送"),
                "chilled": self.shipping(producer1, "chilled", 1200, None, "翌日発送")},
            2: {"chilled": self.shipping(producer2, "chilled", 1100, 10000, "注文から3日以内に発送"),
                "frozen": self.shipping(producer2, "frozen", 1300, None, "注文から5日以内に発送")},
            3: {"frozen": self.shipping(producer3, "frozen", 1500, None, "1週間以内に発送")},
        }
        ProducerStory.objects.create(
            producer=producer1, craft="農薬をできるだけ減らし、葉を取らずに太陽の光で甘みをのせています。",
            method="葉とらず栽培・草生栽培", process="収穫 → 選果 → 箱詰めまで、すべて農園で行います。",
            environment="北アルプスの雪解け水と、昼夜の寒暖差。", reason="祖父の畑を継ぎました。",
            goal="若い人が働きに来たくなる農園にしたい。", publish_status=PublishStatus.PUBLIC)
        ProducerStory.objects.create(
            producer=producer2, craft="塩だけで仕上げる天日干し。", reason="会社員をやめて、地元の港に戻りました。",
            goal="沼津の干物を全国に届けたい。", publish_status=PublishStatus.PUBLIC)
        ProducerStory.objects.create(producer=producer3)

        # 生産者申請が審査中の会員
        pending = Producer.objects.create(
            user=applicant, business_name="高橋茶園", representative_name="高橋 美咲", genre=Producer.Genre.AGRICULTURE,
            prefecture_id=40, city="八女市", production_items="お茶", intro="八女でお茶を育てています。",
            approval_status=Producer.ApprovalStatus.PENDING, publish_status=PublishStatus.DRAFT)
        ProducerApplication.objects.create(producer=pending, status=ProducerApplication.Status.PENDING,
                                           application_reason="直販を始めたいため", submitted_at=now - timedelta(days=1))

        # ---- 商品 ----
        categories = {category.name: category for category in Category.objects.all()}
        products = {}
        for index, (owner, name, category, volume, price, zone, color, extra) in enumerate(PRODUCTS):
            fields = dict(tax_rate=8, description=f"{name}です。{producers[owner].business_name}から直送します。",
                          publish_status=PublishStatus.PUBLIC, popularity_score=len(PRODUCTS) - index)
            fields.update(extra)
            with_image = fields.pop("image", True)
            product = Product.objects.create(
                producer=producers[owner], category=categories[category],
                shipping_setting=settings_by_producer[owner][zone], name=name, volume=volume, price=price, **fields)
            if with_image:
                ProductImage.objects.create(
                    product=product, sort_order=0,
                    image=self.save_image(producers[owner].user, color, f"product-{index + 1:02d}"))
            if index == 0:  # 1件目は画像を2枚にする（商品詳細の画像の切り替え）
                ProductImage.objects.create(
                    product=product, sort_order=1, image=self.save_image(user1, (230, 110, 90), "product-01b", "product-01"))
            # 新着順の確認用に、登録日時を1日ずつずらす
            Product.objects.filter(pk=product.pk).update(created_at=now - timedelta(days=index))
            product.refresh_from_db()
            products[name] = product
        apple = products["安曇野ふじ 家庭用 5kg"]
        lettuce = products["朝どれレタス 3玉"]
        tomato = products["完熟トマト 2kg"]
        rice = products["安曇野のコシヒカリ 5kg"]
        chips = products["りんごのドライチップス"]
        aji = products["沼津 あじの開き干し 10枚"]
        kinme = products["金目鯛の煮付けセット"]
        shirasu = products["釜揚げしらす 500g"]

        # ---- 購入者まわり（お届け先・カート・お気に入り） ----
        Address.objects.create(user=buyer1, recipient_name="佐藤 花子", postal_code="150-0001", prefecture_id=13,
                               city="渋谷区", address_line1="神宮前1-2-3", address_line2="マルシェハイツ101",
                               phone="09011110001", is_default=True)
        CartItem.objects.create(user=buyer1, product=apple, quantity=1)
        CartItem.objects.create(user=buyer1, product=aji, quantity=2)
        FavoriteProduct.objects.create(user=buyer1, product=apple)
        FavoriteProduct.objects.create(user=buyer1, product=kinme)
        FavoriteProducer.objects.create(user=buyer1, producer=producer2, notify=True)

        # ---- 注文10件 ----
        paid, pending_status, failed = Order.PaymentStatus.PAID, Order.PaymentStatus.PENDING, Order.PaymentStatus.FAILED
        status = OrderShipment.Status
        self.order_count = 0
        self.make_order(buyer1, pending_status, 0, [(producer1, "normal", status.UNSHIPPED, [(apple, 1)], {})],
                        ordered_at=now - timedelta(minutes=5))
        self.make_order(buyer1, paid, 1, [(producer1, "normal", status.UNSHIPPED, [(rice, 1), (chips, 2)], {})])
        order3 = self.make_order(buyer1, paid, 4, [
            (producer1, "normal", status.SHIPPED, [(apple, 1)],
             dict(shipped_at=now - timedelta(days=2), tracking_no="1234-5678-9012")),
            (producer1, "chilled", status.SHIPPED, [(tomato, 1)], dict(shipped_at=now - timedelta(days=2))),
            (producer2, "chilled", status.UNSHIPPED, [(aji, 1)], {}),
        ])
        order4 = self.make_order(buyer1, paid, 45, [
            (producer1, "normal", status.DELIVERED, [(apple, 2), (rice, 1), (chips, 1)],
             dict(shipped_at=now - timedelta(days=43), tracking_no="1111-2222-3333")),
            (producer1, "chilled", status.DELIVERED, [(lettuce, 1)], dict(shipped_at=now - timedelta(days=43))),
        ])
        order5 = self.make_order(buyer1, paid, 20, [
            (producer2, "chilled", status.DELIVERED, [(aji, 1), (shirasu, 1)],
             dict(shipped_at=now - timedelta(days=18))),
            (producer2, "frozen", status.DELIVERED, [(kinme, 1)], dict(shipped_at=now - timedelta(days=18))),
            (producer1, "normal", status.DELIVERED, [(apple, 1)], dict(shipped_at=now - timedelta(days=18))),
        ])
        self.make_order(buyer1, paid, 2, [
            (producer1, "normal", status.CANCEL_REQUESTED, [(chips, 3)], dict(cancel_reason="間違えて注文しました。"))])
        self.make_order(buyer1, paid, 6, [
            (producer2, "chilled", status.CANCELED, [(shirasu, 2)],
             dict(cancel_reason="日程が合わなくなりました。", canceled_at=now - timedelta(days=5)))],
            payment_method="konbini")  # コンビニ払いなので返金待ち（運営が返金する）
        self.make_order(buyer1, paid, 30, [
            (producer1, "normal", status.CANCELED, [(rice, 1)],
             dict(cancel_reason="住所を間違えました。", canceled_at=now - timedelta(days=29), refunded=True))])
        self.make_order(None, paid, 1, [(producer1, "normal", status.UNSHIPPED, [(apple, 1)], {})])
        self.make_order(buyer1, failed, 8, [(producer2, "frozen", status.UNSHIPPED, [(kinme, 1)], {})])

        # ---- レビュー10件（発送済み・配達完了の明細に1件ずつ） ----
        comments = ["蜜がたっぷりで、家族にも好評でした。", "新鮮でおいしかったです。", "また注文します。",
                    "梱包がていねいでした。", "少し小ぶりでしたが味は良かったです。"]
        items = OrderItem.objects.filter(
            shipment__order__in=[order3, order4, order5],
            shipment__status__in=[status.SHIPPED, status.DELIVERED]).select_related("product")
        for index, item in enumerate(items.order_by("id")):
            replied = index % 3 == 0
            ProductReview.objects.create(
                order_item=item, product=item.product, user=buyer1, rating=5 - index % 3,
                body=comments[index % len(comments)],
                reply="ありがとうございます。またのご利用をお待ちしています。" if replied else None,
                replied_at=now if replied else None)
        for product_id in set(items.values_list("product_id", flat=True)):
            recalculate_rating(product_id)

        # ---- 体験5件 ----
        def make_experience(number, producer, title, color, publish=PublishStatus.PUBLIC, **extra):
            fields = dict(
                description=f"{title}です。初めての方も歓迎します。", place=f"{producer.business_name}（{producer.city}）",
                price_adult=3000, price_child=1500, age_condition="3歳以上", family_ok=True, beginner_ok=True,
                flow=[{"time": "10:00", "text": "集合・説明"}, {"time": "10:30", "text": "体験"},
                      {"time": "12:00", "text": "解散"}],
                belongings=["汚れてもよい服装", "飲み物"], notes=["雨天の場合は内容を変更することがあります。"],
                cancel_policy="開催の24時間前までキャンセルできます。", booking_deadline_hours=24,
                prefecture=producer.prefecture, publish_status=publish)
            fields.update(extra)
            experience = Experience.objects.create(producer=producer, title=title, **fields)
            ExperienceImage.objects.create(experience=experience, sort_order=0,
                                           image=self.save_image(producer.user, color, f"experience-{number}"))
            return experience

        def make_slot(experience, start_at, capacity=10):
            return ExperienceSlot.objects.create(experience=experience, start_at=start_at, duration_min=120,
                                                 capacity=capacity, reserved_count=0)

        self.reservation_count = 0
        harvest = make_experience(1, producer1, "りんごの収穫体験", (230, 90, 80))
        past = make_slot(harvest, now - timedelta(days=14))
        open_slot = make_slot(harvest, now + timedelta(days=7))
        make_slot(harvest, now + timedelta(days=14))
        self.reserve(past, buyer1, 2, 1, Reservation.Status.ATTENDED)
        self.reserve(open_slot, buyer1, 2, 1)
        full = make_experience(2, producer1, "野菜の植えつけ体験（満席）", (110, 170, 100))
        self.reserve(make_slot(full, now + timedelta(days=10), capacity=4), buyer2, 3, 1)
        closed = make_experience(3, producer2, "干物づくり体験（締め切り後）", (110, 150, 200), price_child=None,
                                 family_ok=False, age_condition="中学生以上")
        make_slot(closed, now + timedelta(hours=12))
        make_experience(4, producer2, "港の朝市ツアー（日程の準備中）", (90, 120, 160))
        make_experience(5, producer1, "下書きの体験", (180, 180, 180), publish=PublishStatus.DRAFT)

        # ---- 求人5件 ----
        def make_job(producer, title, publish=PublishStatus.PUBLIC, **extra):
            fields = dict(
                term_type=Job.TermType.SHORT, pay_unit=Job.PayUnit.DAILY, pay_amount=10000, work_hours="8:00〜15:00",
                work_place=f"{producer.business_name}（{producer.city}）", slots=3,
                description=f"{title}を募集しています。", requirements=["18歳以上の方"],
                belongings=["汚れてもよい服装", "長靴"], notes=["昼食は各自でご用意ください。"],
                inexperienced_ok=True, prefecture=producer.prefecture, publish_status=publish)
            fields.update(extra)
            return Job.objects.create(producer=producer, title=title, **fields)

        def work_date(job, days, needed_count=2):
            return JobWorkDate.objects.create(job=job, work_date=today + timedelta(days=days),
                                              needed_count=needed_count)

        def apply(job, user, application_status, work_dates=()):
            decided = application_status in (JobApplication.Status.HIRED, JobApplication.Status.REJECTED)
            application = JobApplication.objects.create(
                job=job, user=user, status=application_status, message="よろしくお願いします。", answers=[],
                decided_at=now if decided else None)
            for date in work_dates:
                ApplicationWorkDate.objects.create(application=application, work_date=date)

        picking = make_job(producer1, "りんごの収穫スタッフ", period_start=today - timedelta(days=7),
                           period_end=today + timedelta(days=30))
        day1, day2 = work_date(picking, 7), work_date(picking, 8)
        work_date(picking, 14)
        apply(picking, buyer1, JobApplication.Status.APPLIED, [day1, day2])
        apply(picking, buyer2, JobApplication.Status.HIRED, [day1])
        ended = make_job(producer1, "田植えの手伝い（募集期間が終わった）", term_type=Job.TermType.ONE_DAY,
                         period_start=today - timedelta(days=30), period_end=today - timedelta(days=1))
        work_date(ended, -3)
        filled = make_job(producer2, "干物の箱詰めスタッフ（採用枠がいっぱい）", slots=1, pay_unit=Job.PayUnit.HOURLY,
                          pay_amount=1200)
        filled_day = work_date(filled, 5)
        apply(filled, applicant, JobApplication.Status.HIRED, [filled_day])
        make_job(producer2, "水産加工の正社員（長期）", term_type=Job.TermType.LONG, pay_unit=Job.PayUnit.MONTHLY,
                 pay_amount=230000, work_hours="6:00〜15:00（休憩1時間）", slots=2, inexperienced_ok=False)
        make_job(producer1, "下書きの求人", publish=PublishStatus.DRAFT)

    # ------------------------------------------------------------------
    # 部品
    # ------------------------------------------------------------------
    def save_image(self, user, color, *names):
        """写真（なければダミー画像）を images/{ユーザーID}/seed-NNN.jpg に保存し、キーを返す

        本人が画像キーとして送り直せる場所に置く。names は marche/seed_images/ のファイル名（拡張子なし）の候補。
        """
        self.image_count += 1
        return default_storage.save(f"images/{user.id}/seed-{self.image_count:03d}.jpg",
                                    ContentFile(seed_image(names, color)))

    def make_producer(self, number, user, business_name, genre, city, production_items, intro, color, **extra):
        fields = dict(approval_status=Producer.ApprovalStatus.APPROVED, publish_status=PublishStatus.PUBLIC)
        fields.update(extra)
        producer = Producer.objects.create(
            user=user, business_name=business_name, representative_name=f"{user.last_name} {user.first_name}",
            genre=genre, prefecture_id=user.prefecture_id, city=city, production_items=production_items, intro=intro,
            profile_image=self.save_image(user, color, f"producer-{number}-profile"),
            cover_image=self.save_image(user, tuple(min(255, c + 50) for c in color), f"producer-{number}-cover"),
            **fields)
        # 農園の写真は、専用の写真（producer-N-farm）がなければカバーと同じものを使う
        ProducerImage.objects.create(
            producer=producer, sort_order=0,
            image=self.save_image(user, tuple(max(0, c - 30) for c in color), f"producer-{number}-farm",
                                  f"producer-{number}-cover"))
        ProducerApplication.objects.create(
            producer=producer, status=ProducerApplication.Status.APPROVED, application_reason="直販を始めたいため",
            submitted_at=fields["approved_at"] - timedelta(days=2), reviewed_at=fields["approved_at"])
        return producer

    def shipping(self, producer, zone, fee, threshold, lead_time):
        return ShippingSetting.objects.create(producer=producer, temperature_zone=zone, shipping_fee=fee,
                                              free_shipping_threshold=threshold, lead_time_text=lead_time)

    def make_order(self, user, payment_status, days_ago, boxes, payment_method="card", ordered_at=None):
        """注文・箱・明細を作る。boxes は (生産者, 温度帯, 箱の状態, [(商品, 数量)], 箱のそのほかの項目) の並び

        金額は注文APIと同じ数え方（明細は割引後の価格、送料は箱ごと、送料無料ライン以上なら0円）。
        user が None ならゲストの注文。
        """
        self.order_count += 1
        number = self.order_count
        fields = dict(
            order_no=f"{ORDER_PREFIX}{number:04d}", user=user, payment_status=payment_status,
            payment_method=payment_method, access_token_hash=hashlib.sha256(f"seed-{number}".encode()).hexdigest(),
            ship_name="佐藤 花子", ship_postal_code="150-0001", ship_prefecture="東京都", ship_city="渋谷区",
            ship_address_line1="神宮前1-2-3", ship_phone="09011110001", items_total=0, shipping_total=0,
            grand_total=0, tax_8_amount=0, tax_10_amount=0,
            ordered_at=ordered_at or timezone.now() - timedelta(days=days_ago))
        if user is None:
            fields.update(guest_email="guest@example.com", guest_name="田中 一郎", guest_phone="09033330001",
                          ship_name="田中 一郎")
        order = Order.objects.create(**fields)
        items_total = shipping_total = 0
        tax_lines = []
        for producer, zone, shipment_status, lines, extra in boxes:
            extra = dict(extra)
            refunded = extra.pop("refunded", False)
            setting = producer.shipping_settings.get(temperature_zone=zone)
            box_total = sum(product.sale_price * quantity for product, quantity in lines)
            free = setting.free_shipping_threshold is not None and box_total >= setting.free_shipping_threshold
            fee = 0 if free else setting.shipping_fee
            shipment = OrderShipment.objects.create(order=order, producer=producer, temperature_zone=zone,
                                                    shipping_fee=fee, status=shipment_status, **extra)
            if refunded:
                shipment.refunded_amount = box_total + fee
                shipment.save(update_fields=["refunded_amount"])
            for product, quantity in lines:
                subtotal = product.sale_price * quantity
                OrderItem.objects.create(
                    shipment=shipment, product=product, product_name=product.name, unit_price=product.price,
                    discount_rate=product.discount_rate, paid_unit_price=product.sale_price, quantity=quantity,
                    tax_rate=product.tax_rate, subtotal=subtotal)
                tax_lines.append((product.tax_rate, subtotal))
            items_total += box_total
            shipping_total += fee
        order.items_total, order.shipping_total = items_total, shipping_total
        order.grand_total = items_total + shipping_total
        order.tax_8_amount, order.tax_10_amount = tax_amounts(tax_lines, shipping_total)
        order.save(update_fields=["items_total", "shipping_total", "grand_total", "tax_8_amount", "tax_10_amount"])
        return order

    def reserve(self, slot, user, adult_count, child_count, status=Reservation.Status.CONFIRMED):
        """予約を作り、日程の予約人数も増やす"""
        self.reservation_count += 1
        experience = slot.experience
        total = experience.price_adult * adult_count + (experience.price_child or 0) * child_count
        Reservation.objects.create(
            reservation_no=f"{RESERVATION_PREFIX}{self.reservation_count:04d}", slot=slot, user=user,
            adult_count=adult_count, child_count=child_count, infant_count=0,
            representative_name=f"{user.last_name} {user.first_name}", phone=user.phone, total_amount=total,
            status=status, policy_agreed_at=timezone.now())
        slot.reserved_count += adult_count + child_count
        slot.save(update_fields=["reserved_count"])
