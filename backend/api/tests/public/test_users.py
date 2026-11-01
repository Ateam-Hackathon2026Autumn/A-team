"""POST /api/v1/users 新規登録のテスト"""
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.utils import timezone

from marche.models import CartItem, NotificationSetting, User, UserConsent

from ..utils import PASSWORD, ApiTestCase, make_prefecture, make_product, make_user

URL = "/api/v1/users"


def signup_body(**overrides):
    body = {
        "lastName": "山田",
        "firstName": "太郎",
        "email": "taro@example.com",
        "password": PASSWORD,
        "phone": "090-1234-5678",
        "birthDate": "1995-01-01",
        "prefectureId": 13,
        "interests": ["vegetables", "experiences"],
        "agreedToTerms": True,
        "agreedToPrivacyPolicy": True,
        "termsVersion": settings.TERMS_VERSION,
        "privacyPolicyVersion": settings.PRIVACY_POLICY_VERSION,
    }
    body.update(overrides)
    return {k: v for k, v in body.items() if v is not ...}  # ... を渡した項目は送らない


class SignupTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.prefecture = make_prefecture()

    def signup(self, **overrides):
        return self.post_json(URL, signup_body(**overrides))

    def assert_400(self, res, *fields):
        self.assertEqual(res.status_code, 400, res.content)
        body = res.json()
        self.assertEqual(body["errorCode"], "VALIDATION_ERROR")
        for f in fields:
            self.assertIn(f, body["details"])

    # --- 成功 -----------------------------------------------------------------

    def test_success(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.signup(email="  Taro@Example.COM ")
        self.assertEqual(res.status_code, 201, res.content)
        user = User.objects.get()
        self.assertEqual(res.json(), {
            "message": "登録が完了しました。確認メールの配送を受け付けました。",
            "authenticated": True,
            "user": {
                "id": user.id, "email": "taro@example.com", "lastName": "山田", "firstName": "太郎",
                "isProducer": False, "producerApplicationStatus": "not_applied",
                "producerAccountStatus": None, "emailVerified": False,
            },
        })
        # 保存内容
        self.assertEqual(user.phone, "09012345678")  # ハイフンを除いて保存
        self.assertEqual(str(user.birth_date), "1995-01-01")
        self.assertEqual(user.prefecture_id, 13)
        self.assertEqual(user.interests, ["vegetables", "experiences"])
        self.assertIsNone(user.email_verified_at)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(
            sorted(UserConsent.objects.filter(user=user).values_list("document_type", "version")),
            [("privacy_policy", settings.PRIVACY_POLICY_VERSION), ("terms", settings.TERMS_VERSION)],
        )
        self.assertTrue(NotificationSetting.objects.filter(user=user).exists())
        # 確認メール
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["taro@example.com"])
        self.assertIn("/verify-email?token=", mail.outbox[0].body)
        # 自動ログイン（Cookie のセッションでログイン状態になる）
        self.assertTrue(self.client.get("/api/v1/auth/session").json()["authenticated"])
        self.assertEqual(res["Cache-Control"], "no-store")

    def test_optional_fields_can_be_omitted(self):
        res = self.signup(prefectureId=..., interests=...)
        self.assertEqual(res.status_code, 201, res.content)
        user = User.objects.get()
        self.assertIsNone(user.prefecture_id)
        self.assertEqual(user.interests, [])

    def test_guest_cart_is_moved_to_new_account(self):
        product = make_product()
        self.client.get("/api/v1/auth/csrf")
        session = self.client.session
        session.save()
        CartItem.objects.create(session_key=session.session_key, product=product, quantity=2)

        res = self.signup()
        self.assertEqual(res.status_code, 201, res.content)
        item = CartItem.objects.get()
        self.assertEqual((item.user_id, item.session_key, item.quantity), (res.json()["user"]["id"], None, 2))

    # --- 409 ------------------------------------------------------------------

    def test_duplicate_email_is_409_case_insensitive(self):
        make_user(email="taro@example.com")
        res = self.signup(email="TARO@example.com")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "EMAIL_ALREADY_EXISTS")

    def test_policy_version_mismatch_is_409(self):
        res = self.signup(termsVersion="2000-01-01")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "POLICY_VERSION_MISMATCH")
        self.assertFalse(User.objects.exists())

    def test_already_authenticated_is_409(self):
        self.client.force_login(make_user(email="other@example.com"))
        res = self.signup()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["errorCode"], "ALREADY_AUTHENTICATED")

    # --- 403 ------------------------------------------------------------------

    def test_csrf_is_required(self):
        res = self.post_json(URL, signup_body(), csrf=False)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()["errorCode"], "CSRF_FAILED")
        self.assertFalse(User.objects.exists())

    # --- 400 ------------------------------------------------------------------

    def test_required_fields(self):
        res = self.signup(phone=..., birthDate=..., lastName=...)
        self.assert_400(res, "phone", "birthDate", "lastName")

    def test_name_length_and_blank(self):
        self.assert_400(self.signup(lastName="あ" * 11), "lastName")
        self.assert_400(self.signup(firstName="   "), "firstName")
        # 前後の空白は除いてから文字数を数える（10文字ちょうどは OK）
        res = self.signup(lastName="  あいうえおかきくけこ  ")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(User.objects.get().last_name, "あいうえおかきくけこ")

    def test_phone_format(self):
        for ng in ("abc", "090-1234-56789", "0901234", "90-1234-5678", "０９０１２３４５６７８"):
            self.assert_400(self.signup(phone=ng), "phone")

    def test_birth_date_range(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assert_400(self.signup(birthDate=tomorrow), "birthDate")
        self.assert_400(self.signup(birthDate="1899-12-31"), "birthDate")
        self.assert_400(self.signup(birthDate="2026-02-30"), "birthDate")

    def test_interests(self):
        self.assert_400(self.signup(interests=["cooking"]), "interests.0")
        self.assert_400(self.signup(interests=["fruits", "fruits"]), "interests")

    def test_prefecture_must_exist(self):
        self.assert_400(self.signup(prefectureId=99), "prefectureId")

    def test_agreements_must_be_true(self):
        self.assert_400(self.signup(agreedToTerms=False, agreedToPrivacyPolicy=False),
                        "agreedToTerms", "agreedToPrivacyPolicy")

    def test_unknown_field_is_rejected(self):
        self.assert_400(self.signup(isStaff=True), "isStaff")

    def test_password_rules(self):
        self.assert_400(self.signup(password="password"), "password")          # Notion の規則
        self.assert_400(self.signup(password="Password1!"), "password")        # 流出パスワード
        res = self.signup(password="Taroexample1!")                             # メールアドレスに似ている
        self.assert_400(res, "password")
