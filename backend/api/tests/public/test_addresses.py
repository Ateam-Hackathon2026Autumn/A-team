"""お届け先（住所録） のテスト

テスト対象: api/views/public/addresses.py
  - お届け先一覧・登録: GET・POST /api/v1/users/me/addresses
  - お届け先更新・削除: PATCH・DELETE /api/v1/users/me/addresses/:addressId
  - 注文で住所録を使う: POST /api/v1/orders の addressId（services/orders.py の create_order）
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone

from marche.models import Address, Order

from ..utils import ApiTestCase, make_prefecture, make_producer, make_product, make_user

URL = "/api/v1/users/me/addresses"
BODY = {"recipientName": "山田 花子", "postalCode": "1500001", "prefectureId": 13, "city": "渋谷区",
        "addressLine1": "神宮前1-2-3", "addressLine2": "", "phone": "090-1111-2222"}


def detail(address_id):
    return f"{URL}/{address_id}"


class AddressTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.prefecture = make_prefecture()
        self.user = make_user()
        self.signin(self.user.email)

    def create(self, minutes_ago=0, **kw):
        address = Address.objects.create(
            user=kw.pop("user", self.user), recipient_name=kw.pop("recipient_name", "山田 太郎"),
            postal_code="100-0001", prefecture=self.prefecture, city="千代田区", address_line1="1-1",
            phone="0312345678", is_default=kw.pop("is_default", False), **kw)
        Address.objects.filter(pk=address.pk).update(created_at=timezone.now() - timedelta(minutes=minutes_ago))
        return address

    def defaults(self):
        return list(Address.objects.filter(user=self.user, is_default=True).values_list("pk", flat=True))


class AddressListTests(AddressTestCase):
    def test_default_first_then_newest(self):
        old = self.create(minutes_ago=30)
        default = self.create(minutes_ago=20, is_default=True)
        new = self.create(minutes_ago=10)
        self.create(user=make_user(email="other@example.com"))
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([a["id"] for a in res.json()["items"]], [default.id, new.id, old.id])
        self.assertEqual(set(res.json()["items"][0]), {
            "id", "recipientName", "postalCode", "prefectureId", "prefectureName", "city", "addressLine1",
            "addressLine2", "phone", "isDefault", "createdAt", "updatedAt"})
        self.assertEqual(res.json()["items"][0]["prefectureName"], "東京都")

    def test_requires_login(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)


class AddressCreateTests(AddressTestCase):
    def test_first_address_becomes_default(self):
        res = self.post_json(URL, BODY)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual((data["postalCode"], data["phone"], data["addressLine2"], data["isDefault"]),
                         ("150-0001", "09011112222", None, True))

    def test_new_default_clears_others(self):
        first = self.create(is_default=True)
        self.assertFalse(self.post_json(URL, BODY).json()["isDefault"])
        res = self.post_json(URL, {**BODY, "isDefault": True})
        self.assertEqual(self.defaults(), [res.json()["id"]])
        first.refresh_from_db()
        self.assertFalse(first.is_default)

    def test_limit(self):
        for _ in range(10):
            self.create()
        res = self.post_json(URL, BODY)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ADDRESS_LIMIT_EXCEEDED"))

    def test_validation(self):
        res = self.post_json(URL, {**BODY, "postalCode": "150", "prefectureId": 99, "phone": "abc",
                                   "recipientName": ""})
        self.assertEqual(set(res.json()["details"]), {"postalCode", "prefectureId", "phone", "recipientName"})
        res = self.post_json(URL, {**BODY, "nickname": "家"})
        self.assertEqual(set(res.json()["details"]), {"nickname"})
        self.assertFalse(Address.objects.exists())


class AddressUpdateDeleteTests(AddressTestCase):
    def test_patch_only_sent_fields(self):
        address = self.create(is_default=True)
        res = self.patch_json(detail(address.id), {"city": "港区", "addressLine2": "101号室"})
        self.assertEqual(res.status_code, 200)
        address.refresh_from_db()
        self.assertEqual((address.city, address.address_line2, address.recipient_name, address.is_default),
                         ("港区", "101号室", "山田 太郎", True))

    def test_patch_make_default(self):
        default = self.create(is_default=True)
        other = self.create()
        self.assertTrue(self.patch_json(detail(other.id), {"isDefault": True}).json()["isDefault"])
        self.assertEqual(self.defaults(), [other.id])
        res = self.patch_json(detail(other.id), {"isDefault": False})   # 外すだけはできない
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"isDefault"}))
        default.refresh_from_db()
        self.assertFalse(default.is_default)

    def test_patch_empty_body(self):
        address = self.create()
        self.assertEqual(self.patch_json(detail(address.id), {}).status_code, 400)

    def test_delete_default_moves_to_newest(self):
        old = self.create(minutes_ago=30)
        default = self.create(minutes_ago=20, is_default=True)
        newest = self.create(minutes_ago=10)
        self.assertEqual(self.delete_json(detail(default.id)).status_code, 204)
        self.assertEqual(self.defaults(), [newest.id])
        self.assertEqual(self.delete_json(detail(old.id)).status_code, 204)
        self.assertEqual(self.defaults(), [newest.id])
        self.assertEqual(self.delete_json(detail(newest.id)).status_code, 204)
        self.assertFalse(Address.objects.exists())

    def test_others_address_is_404(self):
        theirs = self.create(user=make_user(email="other@example.com"))
        for res in [self.patch_json(detail(theirs.id), {"city": "港区"}), self.delete_json(detail(theirs.id)),
                    self.delete_json(detail(999999)), self.delete_json(detail(2 ** 63))]:
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "ADDRESS_NOT_FOUND"))
        self.assertTrue(Address.objects.filter(pk=theirs.pk).exists())


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class OrderWithAddressIdTests(AddressTestCase):
    """POST /api/v1/orders に addressId を送る"""

    def setUp(self):
        super().setUp()
        self.product = make_product(make_producer(business_name="山田農園"), price=1000)
        self.address = self.create(recipient_name="佐藤 花子", address_line2="マルシェビル")
        patch("api.services.payments.create_checkout_session",
              return_value={"id": "cs_1", "url": "https://checkout.stripe.com/x", "expires_at": 1893456000}).start()
        self.addCleanup(patch.stopall)
        self.post_json("/api/v1/cart/items", {"productId": self.product.id, "quantity": 1})

    def order(self, **kw):
        return self.post_json("/api/v1/orders", {"paymentMethod": "card", "expectedGrandTotal": 2000, **kw})

    def test_order_with_address_id(self):
        res = self.order(addressId=self.address.id)
        self.assertEqual(res.status_code, 201, res.json())
        order = Order.objects.get()
        self.assertEqual((order.ship_name, order.ship_postal_code, order.ship_prefecture, order.ship_city,
                          order.ship_address_line2, order.ship_phone),
                         ("佐藤 花子", "100-0001", "東京都", "千代田区", "マルシェビル", "0312345678"))

    def test_exactly_one_of_address_and_address_id(self):
        shipping = {"lastName": "佐藤", "firstName": "花子", "postalCode": "100-0001", "prefecture": "東京都",
                    "city": "千代田区", "addressLine1": "1-1", "phone": "0312345678"}
        for body in [{}, {"addressId": self.address.id, "shippingAddress": shipping}]:
            res = self.order(**body)
            self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"shippingAddress"}))

    def test_others_address_is_400(self):
        theirs = self.create(user=make_user(email="other@example.com"))
        res = self.order(addressId=theirs.id)
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"addressId"}))
        self.assertFalse(Order.objects.exists())

    def test_guest_cannot_use_address_id(self):
        self.post_json("/api/v1/auth/signout")
        self.post_json("/api/v1/cart/items", {"productId": self.product.id, "quantity": 1})
        res = self.post_json("/api/v1/guest/orders", {
            "addressId": self.address.id, "paymentMethod": "card", "expectedGrandTotal": 2000,
            "guestContact": {"lastName": "鈴木", "firstName": "一郎", "email": "g@example.com", "phone": "09012345678"}})
        self.assertEqual(res.status_code, 400)
        self.assertIn("addressId", res.json()["details"])
