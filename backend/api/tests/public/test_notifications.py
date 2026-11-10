"""サイト内の通知・通知設定 のテスト

テスト対象: api/views/public/notifications.py
  - 通知一覧・未読件数: GET /api/v1/notifications・GET /api/v1/notifications/unread-count
  - 既読にする・すべて既読: PATCH /api/v1/notifications/:notificationId/read・POST /api/v1/notifications/read-all
  - 通知設定: GET・PUT /api/v1/users/me/notification-settings
  - 通知のリンク（linkPath）: 注文の通知に画面のパスが入ること（services/notifications.py）
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import Notification, NotificationSetting, Order

from ...services.orders import mark_paid
from ..utils import ApiTestCase, add_shipment, make_order, make_producer, make_user

URL = "/api/v1/notifications"
SETTINGS_URL = "/api/v1/users/me/notification-settings"


class NotificationTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.signin(self.user.email)

    def notice(self, minutes_ago=0, read=False, user=None, title="発送しました"):
        notification = Notification.objects.create(
            user=user or self.user, notification_type="shipped", title=title, body="本文",
            link_path="/mypage/orders/1", read_at=timezone.now() if read else None)
        Notification.objects.filter(pk=notification.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago))
        return notification


class NotificationListTests(NotificationTestCase):
    def test_list(self):
        old = self.notice(minutes_ago=30, read=True)
        new = self.notice(minutes_ago=10)
        self.notice(user=make_user(email="other@example.com"))
        with self.assertNumQueries(7):  # セッション・ユーザー・件数・一覧・未読件数＋SAVEPOINT・RELEASE
            res = self.client.get(URL)
        data = res.json()
        self.assertEqual((res.status_code, data["total"], data["unreadCount"]), (200, 2, 1))
        self.assertEqual([n["id"] for n in data["items"]], [new.id, old.id])
        self.assertEqual(data["items"][0], {
            "id": new.id, "notificationType": "shipped", "title": "発送しました", "body": "本文",
            "linkPath": "/mypage/orders/1", "isRead": False, "readAt": None,
            "createdAt": data["items"][0]["createdAt"]})
        self.assertTrue(data["items"][1]["isRead"])

    def test_unread_only(self):
        self.notice(read=True)
        unread = self.notice()
        res = self.client.get(URL, {"unreadOnly": "true"})
        self.assertEqual([n["id"] for n in res.json()["items"]], [unread.id])
        self.assertEqual(self.client.get(URL, {"unreadOnly": "1"}).status_code, 400)

    def test_unread_count(self):
        self.notice()
        self.notice(read=True)
        self.assertEqual(self.client.get(f"{URL}/unread-count").json(), {"unreadCount": 1})

    def test_requires_login(self):
        self.post_json("/api/v1/auth/signout")
        for url in [URL, f"{URL}/unread-count", SETTINGS_URL]:
            self.assertEqual(self.client.get(url).status_code, 401)


class NotificationReadTests(NotificationTestCase):
    def test_read(self):
        notification = self.notice()
        res = self.patch_json(f"{URL}/{notification.id}/read")
        self.assertEqual((res.status_code, res.json()["isRead"]), (200, True))
        first_read = res.json()["readAt"]
        res = self.patch_json(f"{URL}/{notification.id}/read")   # 2回目はそのまま
        self.assertEqual((res.status_code, res.json()["readAt"]), (200, first_read))

    def test_others_notification_is_404(self):
        theirs = self.notice(user=make_user(email="other@example.com"))
        for notification_id in [theirs.id, 999999, 2 ** 63]:
            res = self.patch_json(f"{URL}/{notification_id}/read")
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOTIFICATION_NOT_FOUND"))
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_read_all(self):
        self.notice()
        self.notice()
        theirs = self.notice(user=make_user(email="other@example.com"))
        res = self.post_json(f"{URL}/read-all")
        self.assertEqual((res.status_code, res.json()), (200, {"unreadCount": 0}))
        self.assertFalse(Notification.objects.filter(user=self.user, read_at__isnull=True).exists())
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)
        self.assertEqual(self.post_json(f"{URL}/read-all", csrf=False).status_code, 403)


class NotificationSettingTests(NotificationTestCase):
    def test_get_creates_defaults(self):
        self.assertFalse(NotificationSetting.objects.exists())   # make_user では作られない
        res = self.client.get(SETTINGS_URL)
        self.assertEqual(res.json(), {"emailMessage": True, "emailFavorite": True, "emailNews": True})
        self.assertEqual(NotificationSetting.objects.count(), 1)

    def test_put(self):
        res = self.put_json(SETTINGS_URL, {"emailMessage": False, "emailFavorite": True, "emailNews": False})
        self.assertEqual(res.json(), {"emailMessage": False, "emailFavorite": True, "emailNews": False})
        setting = NotificationSetting.objects.get(user=self.user)
        self.assertEqual((setting.email_message, setting.email_news, setting.push_enabled), (False, False, False))

    def test_put_validation(self):
        res = self.put_json(SETTINGS_URL, {"emailMessage": False})
        self.assertEqual(set(res.json()["details"]), {"emailFavorite", "emailNews"})
        res = self.put_json(SETTINGS_URL, {"emailMessage": False, "emailFavorite": True, "emailNews": True,
                                           "pushEnabled": True})
        self.assertEqual(set(res.json()["details"]), {"pushEnabled"})


class LinkPathTests(ApiTestCase):
    def test_order_notifications_have_links(self):
        buyer = make_user(email="buyer@example.com")
        producer = make_producer()
        order = make_order(user=buyer, payment_status=Order.PaymentStatus.PENDING)
        add_shipment(order, producer)
        mark_paid(order.id)
        self.assertEqual(Notification.objects.get(user=buyer).link_path, f"/mypage/orders/{order.id}")
        self.assertEqual(Notification.objects.get(user=producer.user).link_path, f"/dashboard/orders/{order.id}")
