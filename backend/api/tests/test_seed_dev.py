"""開発用のデータ投入コマンド（seed_dev）のテスト"""
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone

from marche.management.commands import seed_dev
from marche.management.commands.seed_dev import DEV_PASSWORD, REVIEW_TEXT, SEED_EMAILS
from marche.models import (Area, Category, Experience, ExperienceSlot, Job, JobApplication, JobWorkDate, Order,
                            Producer, ProducerStory, Product, ProductImage, ProductReview, Prefecture,
                            PublishStatus, Reservation, User)

from .utils import ApiTestCase, make_product, make_user


def seed(*args):
    out = StringIO()
    call_command("seed_dev", *args, stdout=out)
    return out.getvalue()


@override_settings(DEBUG=True)
class SeedDevTests(ApiTestCase):
    def test_refuses_outside_debug(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                seed()
        self.assertFalse(User.objects.exists())

    def test_creates_data(self):
        output = seed()
        self.assertIn("buyer1@example.com", output)
        self.assertEqual(User.objects.filter(email__in=SEED_EMAILS).count(), 10)
        self.assertEqual(Producer.objects.filter(approval_status="approved").count(), 7)
        self.assertEqual(Product.objects.count(), 31)
        self.assertEqual(Experience.objects.count(), 8)
        self.assertEqual(Job.objects.count(), 8)
        self.assertEqual(Order.objects.count(), 13)
        self.assertEqual(ProductReview.objects.count(), 18)
        self.assertEqual(ProducerStory.objects.filter(publish_status=PublishStatus.PUBLIC).count(), 5)
        # 状態の違う商品がそろっている
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.DRAFT).exists())
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.PUBLIC, stock=0).exists())
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.PUBLIC, stock__isnull=True).exists())
        # 評価順の確認用に、レビューが3件ある商品がある
        apple = Product.objects.get(name="安曇野ふじ 家庭用 5kg")
        self.assertEqual(apple.review_count, 3)
        self.assertIsNotNone(apple.rating_avg)
        self.assertGreaterEqual(Product.objects.filter(review_count__gte=3).count(), 3)
        # 注文の合計は、明細と送料の合計と合っている
        for order in Order.objects.all():
            self.assertEqual(order.grand_total, order.items_total + order.shipping_total)

    def test_second_run_adds_nothing(self):
        seed()
        output = seed()
        self.assertIn("もう入っています", output)
        self.assertEqual(User.objects.count(), 10)
        self.assertEqual(Product.objects.count(), 31)
        self.assertEqual(Order.objects.count(), 13)

    def test_reset_recreates_only_seed_data(self):
        other = make_product(name="ほかの人の商品")  # このコマンドと関係のないデータ
        mine = make_user(email="someone@example.com")
        seed()
        # 開発用アカウントで画面から足したデータ（注文番号が TM-SEED- でない注文）も一緒に消える
        buyer = User.objects.get(email="buyer1@example.com")
        Order.objects.filter(order_no="TM-SEED-0002").update(order_no="TM-20261113-000001")
        seed("--reset")
        self.assertEqual(Product.objects.count(), 32)
        self.assertEqual(Order.objects.count(), 13)
        self.assertEqual(User.objects.count(), 10 + 2)  # 開発用10人＋ほかの商品の生産者＋someone
        self.assertTrue(Product.objects.filter(pk=other.pk).exists())
        self.assertTrue(User.objects.filter(pk=mine.pk).exists())
        self.assertFalse(User.objects.filter(pk=buyer.pk).exists())  # 作り直されて ID が変わる

    def test_seeded_accounts_work_with_api(self):
        seed()
        # 公開側：公開中で、生産者も公開中の商品だけ（下書き・非公開・掲載停止・停止中の生産者の商品は出ない）
        products = self.client.get("/api/v1/products?pageSize=100").json()
        self.assertEqual(products["total"], 26)
        self.assertTrue(all(item["thumbnailUrl"] for item in products["items"]))
        self.assertEqual(self.client.get("/api/v1/producers").json()["total"], 6)
        self.assertEqual(self.client.get("/api/v1/experiences").json()["total"], 7)
        self.assertEqual(self.client.get("/api/v1/jobs").json()["total"], 7)

        # 購入者：ログインして、カート・注文履歴が見られる
        self.assertEqual(self.signin("buyer1@example.com", DEV_PASSWORD).status_code, 200)
        cart = self.client.get("/api/v1/cart").json()
        self.assertEqual(len(cart["items"]), 2)
        self.assertEqual(len(cart["shipments"]), 2)  # 生産者が違うので箱が2つ
        self.assertTrue(cart["canCheckout"])
        self.assertEqual(self.client.get("/api/v1/users/me/orders").json()["total"], 9)  # ゲストの1件は含めない
        self.post_json("/api/v1/auth/signout")

        # 生産者：ダッシュボードが見られ、入れた画像のキーをそのまま更新で送れる
        self.assertEqual(self.signin("producer1@example.com", DEV_PASSWORD).status_code, 200)
        summary = self.client.get("/api/v1/dashboard/summary").json()
        self.assertEqual(summary["publishedProductCount"], 9)
        self.assertGreater(summary["todo"]["unshippedCount"], 0)
        image = ProductImage.objects.filter(product__name="シナノゴールド 3kg").first()
        response = self.patch_json(f"/api/v1/dashboard/products/{image.product_id}",
                                   {"imageKeys": [image.image.name], "publishStatus": "public"})
        self.assertEqual(response.status_code, 200, response.content)

    def test_uses_photo_when_file_exists(self):
        """marche/seed_images/ に同じ名前の写真があればそれを使い、なければ色つきの画像にする"""
        with tempfile.TemporaryDirectory() as folder:
            photo = seed_dev.dummy_image((1, 2, 3))
            (Path(folder) / "product-02.jpg").write_bytes(photo)
            with mock.patch.object(seed_dev, "SEED_IMAGE_DIR", Path(folder)):
                seed()
        with_photo = ProductImage.objects.get(product__name="シナノゴールド 3kg")
        without_photo = ProductImage.objects.get(product__name="朝どれレタス 3玉")
        self.assertEqual(with_photo.image.read(), photo)
        self.assertNotEqual(without_photo.image.read(), photo)

    def test_photos_are_in_repository(self):
        """公開データと審査中生産者に対応する写真ファイルが存在する"""
        names = [f"product-{n:02d}" for n in range(1, 32) if n != 10]
        names += ["product-01b", "product-29b"]
        names += [f"producer-{n}-{kind}" for n in range(1, 8) for kind in ("profile", "cover", "farm")]
        names += [f"producer-pending-{kind}" for kind in ("profile", "cover")]
        names += [f"experience-{n}" for n in range(1, 9)]
        names += [f"job-{n}" for n in range(1, 8)]
        for name in names:
            self.assertTrue((seed_dev.SEED_IMAGE_DIR / f"{name}.jpg").is_file(), name)
        seed()
        image = ProductImage.objects.get(product__name="シナノゴールド 3kg")
        self.assertEqual(image.image.read(), (seed_dev.SEED_IMAGE_DIR / "product-02.jpg").read_bytes())
        # 求人：公開の7件はカバー写真あり、下書きはなし
        picking = Job.objects.get(title="安曇野りんごの選果・箱詰めスタッフ")
        self.assertEqual(picking.cover_image.read(), (seed_dev.SEED_IMAGE_DIR / "job-1.jpg").read_bytes())
        self.assertEqual(Job.objects.exclude(cover_image="").count(), 7)
        self.assertFalse(Job.objects.get(title="下書きの求人").cover_image)

    def test_masters_already_exist_with_other_ids(self):
        """同じ名前のカテゴリー・エリアが別の ID でもうあっても、失敗せずに足りない分だけ入れる"""
        Category.objects.create(name="仮のカテゴリー", sort_order=99)
        vegetables = Category.objects.create(name="野菜", sort_order=1)  # フィクスチャーの ID（1）とは違う ID になる
        Area.objects.create(name="仮のエリア", sort_order=99)
        kanto = Area.objects.create(name="関東", sort_order=3)
        seed()
        seed("--reset")
        self.assertEqual(Category.objects.filter(name="野菜").get().pk, vegetables.pk)
        self.assertEqual(Category.objects.count(), 8 + 1)
        self.assertEqual(Area.objects.count(), 7 + 1)
        self.assertEqual(Prefecture.objects.count(), 47)
        self.assertEqual(Prefecture.objects.get(pk=13).area, kanto)
        self.assertEqual(Product.objects.filter(category=vegetables).count(), 3)

    def test_public_demo_content_is_actionable(self):
        seed()
        visible = Producer.objects.filter(approval_status=Producer.ApprovalStatus.APPROVED,
                                          publish_status=PublishStatus.PUBLIC)
        self.assertEqual(visible.count(), 6)
        self.assertEqual(visible.filter(genre=Producer.Genre.AGRICULTURE).count(), 3)
        self.assertEqual(visible.filter(genre=Producer.Genre.FISHERY).count(), 1)
        self.assertEqual(visible.filter(genre=Producer.Genre.LIVESTOCK).count(), 2)
        self.assertGreaterEqual(visible.filter(featured_score__gt=0).count(), 3)
        this_year = timezone.localdate().year
        self.assertGreaterEqual(visible.filter(career_start_year__range=(this_year - 5, this_year)).count(), 3)
        producers_response = self.client.get("/api/v1/producers?pageSize=100").json()["items"]
        self.assertGreaterEqual(sum("new_farmer" in item["badges"] for item in producers_response), 3)
        self.assertGreaterEqual(self.client.get("/api/v1/producers?featured=true").json()["total"], 3)
        self.assertEqual(producers_response[0]["businessName"], "海風水産")
        self.assertNotIn("new_farmer", next(item for item in producers_response
                                              if item["businessName"] == "十勝のびのび牧場")["badges"])
        self.assertEqual(Category.objects.filter(products__publish_status=PublishStatus.PUBLIC,
                                                 products__producer__in=visible).distinct().count(), 8)
        self.assertTrue(all(product.method and len(product.description) > 30 for product in Product.objects.all()))
        stories = ProducerStory.objects.filter(producer__in=visible, publish_status=PublishStatus.PUBLIC)
        self.assertEqual(stories.count(), 5)
        self.assertTrue(all(all(getattr(story, field) for field in
                                ("craft", "reason", "method", "process", "environment", "goal")) for story in stories))

        buyer = User.objects.get(email="buyer1@example.com")
        open_experiences = Experience.objects.filter(producer__in=visible, publish_status=PublishStatus.PUBLIC,
                                                      experience_slots__start_at__gt=timezone.now()).distinct()
        available_experiences = [experience for experience in open_experiences if any(
            slot.reserved_count < slot.capacity and
            not Reservation.objects.filter(slot=slot, user=buyer).exists() and
            slot.start_at > timezone.now() + timedelta(hours=experience.booking_deadline_hours)
            for slot in ExperienceSlot.objects.filter(experience=experience))]
        self.assertGreaterEqual(len(available_experiences), 3)
        for experience in available_experiences:
            slots = self.client.get(f"/api/v1/experiences/{experience.pk}").json()["slots"]["items"]
            self.assertTrue(any(slot["bookable"] and
                                not Reservation.objects.filter(slot_id=slot["id"], user=buyer).exists()
                                for slot in slots))

        open_jobs = Job.objects.filter(producer__in=visible, publish_status=PublishStatus.PUBLIC,
                                       period_start__lte=timezone.localdate(), period_end__gte=timezone.localdate())
        actionable_jobs = [job for job in open_jobs if
                           not JobApplication.objects.filter(job=job, user=buyer).exists() and
                           JobWorkDate.objects.filter(job=job, work_date__gte=timezone.localdate()).exists()]
        self.assertGreaterEqual(len(actionable_jobs), 3)
        self.assertTrue(any(job.pay_unit == Job.PayUnit.HOURLY and job.pay_amount >= 1400
                            for job in actionable_jobs))
        self.assertEqual(self.signin("buyer1@example.com", DEV_PASSWORD).status_code, 200)
        for job in actionable_jobs:
            detail = self.client.get(f"/api/v1/jobs/{job.pk}").json()
            self.assertTrue(detail["isAcceptingApplications"])
            self.assertFalse(detail["hasApplied"])
            self.assertTrue(any(day["isSelectable"] for day in detail["workDates"]["items"]))

    def test_tokachi_dairy_products_are_public(self):
        seed()
        producer = Producer.objects.get(business_name="十勝のびのび牧場")
        self.assertEqual(producer.publish_status, PublishStatus.PUBLIC)
        products = list(Product.objects.filter(producer=producer).order_by("id"))
        self.assertEqual([product.name for product in products], [
            "十勝のびのび牧場のノンホモ牛乳", "十勝の手づくりナチュラルチーズ"])
        self.assertEqual([product.category.name for product in products], ["その他", "加工品"])
        for product in products:
            self.assertEqual(product.publish_status, PublishStatus.PUBLIC)
            self.assertEqual(product.shipping_setting.temperature_zone, "chilled")
            self.assertTrue(product.description and product.method)
            self.assertTrue(ProductImage.objects.filter(product=product).exists())
        response = self.client.get(f"/api/v1/products?producerId={producer.pk}").json()
        self.assertEqual(response["total"], 2)
        self.assertTrue(all(item["thumbnailUrl"] for item in response["items"]))

    def test_review_text_and_delivery_match_products_and_buyer(self):
        seed()
        for review in ProductReview.objects.select_related("product").all():
            self.assertIn(review.body, REVIEW_TEXT[review.product.name])
        buyer2_orders = Order.objects.filter(user__email="buyer2@example.com")
        self.assertEqual(buyer2_orders.count(), 3)
        self.assertTrue(all(order.ship_name == "鈴木 大輔" and order.ship_prefecture == "大阪府"
                            for order in buyer2_orders))

    def test_experience_times_and_home_slots_remain_bookable(self):
        seed()
        for slot in ExperienceSlot.objects.all():
            local_start = timezone.localtime(slot.start_at)
            self.assertEqual((local_start.hour, local_start.minute),
                             (13, 0) if slot.experience.title == "沼津港・伝統の天日干し干物づくり体験"
                             and local_start.date() == timezone.localdate() else (10, 0))

        # デモ実行の数日後にも、ホーム先頭の体験 3 件は実際の API で予約可能な日程を持つ。
        seeded_now = timezone.now()
        for days in (3, 14):
            with mock.patch("django.utils.timezone.now", return_value=seeded_now + timedelta(days=days)):
                summaries = self.client.get("/api/v1/experiences?pageSize=100").json()["items"]
                upcoming = sorted((item for item in summaries if item["nextStartAt"]),
                                  key=lambda item: item["nextStartAt"])[:3]
                self.assertEqual(len(upcoming), 3)
                for summary in upcoming:
                    detail = self.client.get(f"/api/v1/experiences/{summary['id']}").json()
                    self.assertTrue(any(slot["bookable"] for slot in detail["slots"]["items"]))
