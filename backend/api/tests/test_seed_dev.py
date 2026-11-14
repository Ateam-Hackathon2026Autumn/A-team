"""開発用のデータ投入コマンド（seed_dev）のテスト"""
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import override_settings

from marche.management.commands import seed_dev
from marche.management.commands.seed_dev import DEV_PASSWORD, SEED_EMAILS
from marche.models import (Area, Category, Experience, Job, Order, Producer, Product, ProductImage, ProductReview, Prefecture,
                            PublishStatus, User)

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
        self.assertEqual(User.objects.filter(email__in=SEED_EMAILS).count(), 6)
        self.assertEqual(Producer.objects.filter(approval_status="approved").count(), 3)
        self.assertEqual(Product.objects.count(), 20)
        self.assertEqual(Experience.objects.count(), 5)
        self.assertEqual(Job.objects.count(), 5)
        self.assertEqual(Order.objects.count(), 10)
        self.assertEqual(ProductReview.objects.count(), 10)
        # 状態の違う商品がそろっている
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.DRAFT).exists())
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.PUBLIC, stock=0).exists())
        self.assertTrue(Product.objects.filter(publish_status=PublishStatus.PUBLIC, stock__isnull=True).exists())
        # 評価順の確認用に、レビューが3件ある商品がある
        apple = Product.objects.get(name="安曇野ふじ 家庭用 5kg")
        self.assertEqual(apple.review_count, 3)
        self.assertIsNotNone(apple.rating_avg)
        # 注文の合計は、明細と送料の合計と合っている
        for order in Order.objects.all():
            self.assertEqual(order.grand_total, order.items_total + order.shipping_total)

    def test_second_run_adds_nothing(self):
        seed()
        output = seed()
        self.assertIn("もう入っています", output)
        self.assertEqual(User.objects.count(), 6)
        self.assertEqual(Product.objects.count(), 20)
        self.assertEqual(Order.objects.count(), 10)

    def test_reset_recreates_only_seed_data(self):
        other = make_product(name="ほかの人の商品")  # このコマンドと関係のないデータ
        mine = make_user(email="someone@example.com")
        seed()
        # 開発用アカウントで画面から足したデータ（注文番号が TM-SEED- でない注文）も一緒に消える
        buyer = User.objects.get(email="buyer1@example.com")
        Order.objects.filter(order_no="TM-SEED-0002").update(order_no="TM-20261113-000001")
        seed("--reset")
        self.assertEqual(Product.objects.count(), 21)
        self.assertEqual(Order.objects.count(), 10)
        self.assertEqual(User.objects.count(), 6 + 2)  # 開発用6人＋ほかの商品の生産者＋someone
        self.assertTrue(Product.objects.filter(pk=other.pk).exists())
        self.assertTrue(User.objects.filter(pk=mine.pk).exists())
        self.assertFalse(User.objects.filter(pk=buyer.pk).exists())  # 作り直されて ID が変わる

    def test_seeded_accounts_work_with_api(self):
        seed()
        # 公開側：公開中で、生産者も公開中の商品だけ（下書き・非公開・掲載停止・停止中の生産者の商品は出ない）
        products = self.client.get("/api/v1/products?pageSize=100").json()
        self.assertEqual(products["total"], 15)
        self.assertTrue(all(item["thumbnailUrl"] for item in products["items"]))
        self.assertEqual(self.client.get("/api/v1/producers").json()["total"], 2)
        self.assertEqual(self.client.get("/api/v1/experiences").json()["total"], 4)
        self.assertEqual(self.client.get("/api/v1/jobs").json()["total"], 4)

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
        """確認用の写真（商品19・生産者6・体験5）がそろっていて、入れたデータに使われる"""
        names = [f"product-{n:02d}" for n in range(1, 21) if n != 10]  # 10番は画像なしの下書き
        names += [f"producer-{n}-{kind}" for n in (1, 2, 3) for kind in ("profile", "cover")]
        names += [f"experience-{n}" for n in range(1, 6)]
        for name in names:
            self.assertTrue((seed_dev.SEED_IMAGE_DIR / f"{name}.jpg").is_file(), name)
        seed()
        image = ProductImage.objects.get(product__name="シナノゴールド 3kg")
        self.assertEqual(image.image.read(), (seed_dev.SEED_IMAGE_DIR / "product-02.jpg").read_bytes())

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
