"""認証（CSRF取得・ログイン・ログインチェック・ログアウト。メール認証は拡張で無効）のテスト"""

from django.utils import timezone

from marche.models import CartItem, Producer, PublishStatus

from ..utils import PASSWORD, ApiTestCase, make_producer, make_product, make_user

SESSION = "/api/v1/auth/session"
SIGNIN = "/api/v1/auth/signin"
SIGNOUT = "/api/v1/auth/signout"
RESEND = "/api/v1/auth/email-verification/resend"
CONFIRM = "/api/v1/auth/email-verification/confirm"


class CsrfAndSessionTests(ApiTestCase):
    def test_csrf_returns_token_and_cookie_without_session(self):
        res = self.client.get("/api/v1/auth/csrf")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["csrfToken"])
        self.assertIn("csrftoken", res.cookies)
        self.assertNotIn("sessionid", res.cookies)

    def test_session_when_anonymous(self):
        res = self.client.get(SESSION)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"authenticated": False, "user": None})
        self.assertEqual(len(res.cookies), 0)  # セッションも CSRF Cookie も作らない

    def test_session_when_inactive_user(self):
        user = make_user(is_active=False)
        self.client.force_login(user)
        self.assertEqual(self.client.get(SESSION).json(), {"authenticated": False, "user": None})


class SigninTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()

    def test_success(self):
        res = self.signin("taro@example.com")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json(), {
            "message": "ログインしました。",
            "authenticated": True,
            "user": {
                "id": self.user.id, "email": "taro@example.com", "lastName": "山田", "firstName": "太郎",
                "isProducer": False, "producerApplicationStatus": "not_applied",
                "producerAccountStatus": None, "emailVerified": False,
            },
        })
        self.assertIn("sessionid", res.cookies)
        self.assertEqual(self.client.get(SESSION).json()["user"]["id"], self.user.id)

    def test_email_is_case_insensitive(self):
        self.assertEqual(self.signin("  TARO@Example.com ").status_code, 200)

    def test_invalid_credentials_are_all_401(self):
        make_user(email="stopped@example.com", is_active=False)
        make_user(email="deleted@example.com", is_active=False, deleted_at=timezone.now())
        cases = [("taro@example.com", "WrongPass123!"), ("nobody@example.com", PASSWORD),
                 ("stopped@example.com", PASSWORD), ("deleted@example.com", PASSWORD)]
        for email, password in cases:
            res = self.signin(email, password)
            self.assertEqual(res.status_code, 401, email)
            self.assertEqual(res.json(), {"errorCode": "INVALID_CREDENTIALS",
                                          "errorMsg": "メールアドレスまたはパスワードが正しくありません。"})
            self.assertEqual(res["WWW-Authenticate"], 'Session realm="api"')

    def test_already_authenticated_is_409(self):
        self.signin("taro@example.com")
        res = self.signin("taro@example.com")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "ALREADY_AUTHENTICATED")

    def test_csrf_is_required(self):
        res = self.post_json(SIGNIN, {"email": "taro@example.com", "password": PASSWORD}, csrf=False)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["errorCode"], "CSRF_FAILED")

    def test_validation(self):
        res = self.post_json(SIGNIN, {"email": "not-an-email", "remember": True})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(set(res.json()["details"]), {"remember"})
        res = self.post_json(SIGNIN, {"email": "not-an-email"})
        self.assertEqual(set(res.json()["details"]), {"email", "password"})

    def test_session_is_rotated(self):
        self.client.get("/api/v1/auth/csrf")
        guest = self.client.session
        guest.save()
        self.signin("taro@example.com")
        self.assertNotEqual(self.client.session.session_key, guest.session_key)

    def test_guest_cart_is_merged(self):
        carrot, onion, potato = make_product(name="にんじん"), make_product(name="たまねぎ"), make_product(name="じゃがいも")
        CartItem.objects.create(user=self.user, product=carrot, quantity=8)
        CartItem.objects.create(user=self.user, product=potato, quantity=1)

        self.client.get("/api/v1/auth/csrf")
        session = self.client.session
        session.save()
        CartItem.objects.create(session_key=session.session_key, product=carrot, quantity=5)
        CartItem.objects.create(session_key=session.session_key, product=onion, quantity=2)

        self.assertEqual(self.signin("taro@example.com").status_code, 200)
        cart = {i.product_id: i.quantity for i in CartItem.objects.filter(user=self.user)}
        self.assertEqual(cart, {carrot.id: 10, onion.id: 2, potato.id: 1})  # 同じ商品は合算して上限10
        self.assertFalse(CartItem.objects.filter(user__isnull=True).exists())


class ProducerStatusTests(ApiTestCase):
    def status_of(self, user):
        self.client.force_login(user)
        u = self.client.get(SESSION).json()["user"]
        return u["isProducer"], u["producerApplicationStatus"], u["producerAccountStatus"]

    def test_statuses(self):
        cases = [
            (Producer.ApprovalStatus.PENDING, PublishStatus.DRAFT, (False, "pending", "active")),
            (Producer.ApprovalStatus.RETURNED, PublishStatus.DRAFT, (False, "returned", "active")),
            (Producer.ApprovalStatus.REJECTED, PublishStatus.DRAFT, (False, "rejected", "active")),
            (Producer.ApprovalStatus.APPROVED, PublishStatus.PUBLIC, (True, "approved", "active")),
            # 掲載停止中もダッシュボードの閲覧・発送はできるので isProducer は true
            (Producer.ApprovalStatus.APPROVED, PublishStatus.SUSPENDED, (True, "approved", "suspended")),
        ]
        for i, (approval, publish, expected) in enumerate(cases):
            user = make_user(email=f"p{i}@example.com")
            make_producer(user=user, approval=approval, publish=publish)
            self.assertEqual(self.status_of(user), expected, (approval, publish))


class SignoutTests(ApiTestCase):
    def test_signout(self):
        make_user()
        self.signin("taro@example.com")
        res = self.post_json(SIGNOUT)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"message": "ログアウトしました。"})
        self.assertEqual(res.cookies["sessionid"].value, "")  # Cookie を削除
        self.assertFalse(self.client.get(SESSION).json()["authenticated"])

    def test_signout_when_anonymous_is_200(self):
        self.assertEqual(self.post_json(SIGNOUT).status_code, 200)

    def test_csrf_is_required_even_when_anonymous(self):
        res = self.post_json(SIGNOUT, csrf=False)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["errorCode"], "CSRF_FAILED")


class EmailVerificationDisabledTests(ApiTestCase):
    """メール認証は拡張。確認・再送の API は公開していない"""

    def test_endpoints_are_not_found(self):
        self.client.force_login(make_user())
        self.assertEqual(self.post_json(RESEND).status_code, 404)
        self.assertEqual(self.post_json(CONFIRM, {"token": "abc"}).status_code, 404)
