"""会員登録・自分のアカウント のテスト

テスト対象: api/views/public/users.py（services/anonymize.py）
  - 新規登録: POST /api/v1/users
  - 本人情報の取得・更新: GET・PATCH /api/v1/users/me
  - メールアドレスの変更: PUT /api/v1/users/me/email
  - パスワード変更: PUT /api/v1/users/me/password
  - 退会: DELETE /api/v1/users/me
"""
from datetime import date, timedelta

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from marche.models import (
    Address,
    CartItem,
    Experience,
    ExperienceSlot,
    FavoriteProduct,
    Job,
    JobApplication,
    NotificationSetting,
    Order,
    Reservation,
    User,
    UserConsent,
)

from ..utils import (
    PASSWORD,
    ApiTestCase,
    add_shipment,
    make_order,
    make_prefecture,
    make_producer,
    make_product,
    make_user,
)

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


# =========================================================
# 本人情報（マイページ）
# =========================================================

ME_URL = "/api/v1/users/me"
NEW_PASSWORD = "NewPass#2026x"


class MeTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()  # 回数制限のカウントを毎回まっさらにする
        self.prefecture = make_prefecture()
        self.user = make_user(email="taro@example.com", phone="09012345678", birth_date=date(1995, 1, 1),
                              prefecture=self.prefecture, interests=["vegetables"])
        self.signin(self.user.email)


class MeTests(MeTestCase):
    def test_get(self):
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["email"], "taro@example.com")
        self.assertEqual(res.json()["profile"], {"phone": "09012345678", "birthDate": "1995-01-01",
                                                 "prefectureId": 13, "interests": ["vegetables"]})

    def test_requires_login(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(ME_URL).status_code, 401)

    def test_patch_only_sent_fields(self):
        res = self.patch_json(ME_URL, {"firstName": " 次郎 ", "phone": "03-1234-5678", "interests": []})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["firstName"], "次郎")
        self.assertEqual(res.json()["profile"]["interests"], [])
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.last_name, self.user.phone, self.user.birth_date),
                         ("次郎", "山田", "0312345678", date(1995, 1, 1)))

    def test_patch_prefecture_can_be_cleared(self):
        res = self.patch_json(ME_URL, {"prefectureId": None})
        self.assertIsNone(res.json()["profile"]["prefectureId"])

    def test_patch_validation(self):
        cases = [
            ({}, "nonFieldErrors"),
            ({"email": "new@example.com"}, "email"),                  # メールは専用のAPIで
            ({"lastName": "あ" * 11}, "lastName"),
            ({"firstName": "   "}, "firstName"),
            ({"phone": None}, "phone"),                               # 削除はできない
            ({"birthDate": None}, "birthDate"),
            ({"birthDate": (timezone.localdate() + timedelta(days=1)).isoformat()}, "birthDate"),
            ({"prefectureId": 99}, "prefectureId"),
            ({"interests": ["vegetables", "vegetables"]}, "interests"),
            ({"interests": ["golf"]}, "interests.0"),
        ]
        for body, key in cases:
            res = self.patch_json(ME_URL, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "09012345678")

    def test_patch_requires_csrf(self):
        self.assertEqual(self.patch_json(ME_URL, {"firstName": "次郎"}, csrf=False).status_code, 403)


class EmailChangeTests(MeTestCase):
    URL = "/api/v1/users/me/email"

    def test_change(self):
        User.objects.filter(pk=self.user.pk).update(email_verified_at=timezone.now())
        with self.captureOnCommitCallbacks(execute=True):
            res = self.put_json(self.URL, {"email": "New@Example.com", "currentPassword": PASSWORD})
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()["user"]["email"], res.json()["user"]["emailVerified"]),
                         ("new@example.com", False))
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["new@example.com", "taro@example.com"])
        verify = next(m for m in mail.outbox if m.to == ["new@example.com"])
        self.assertIn("/verify-email?token=", verify.body)
        # 新しいアドレスでログインでき、今のセッションは続く
        self.assertTrue(self.client.get("/api/v1/auth/session").json()["authenticated"])
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.signin("new@example.com").status_code, 200)

    def test_errors(self):
        make_user(email="used@example.com")
        res = self.put_json(self.URL, {"email": "used@example.com", "currentPassword": PASSWORD})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "EMAIL_ALREADY_EXISTS"))
        res = self.put_json(self.URL, {"email": "new@example.com", "currentPassword": "wrong"})
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"currentPassword"}))
        res = self.put_json(self.URL, {"email": "TARO@example.com", "currentPassword": PASSWORD})
        self.assertEqual(set(res.json()["details"]), {"email"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "taro@example.com")


class PasswordChangeTests(MeTestCase):
    URL = "/api/v1/users/me/password"

    def test_change_keeps_this_session(self):
        other = self.client_class()
        other.post("/api/v1/auth/signin", {"email": self.user.email, "password": PASSWORD}, format="json")
        self.assertEqual(other.get(ME_URL).status_code, 200)
        with self.captureOnCommitCallbacks(execute=True):
            res = self.put_json(self.URL, {"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD})
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self.client.get(ME_URL).status_code, 200)   # この端末はログインしたまま
        self.assertEqual(other.get(ME_URL).status_code, 401)          # ほかの端末はログアウト
        self.assertEqual(mail.outbox[0].subject, "【つながるマルシェ】パスワードが変更されました")
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.signin(self.user.email, NEW_PASSWORD).status_code, 200)

    def test_errors(self):
        cases = [
            ({"currentPassword": "wrong", "newPassword": NEW_PASSWORD}, "currentPassword"),
            ({"currentPassword": PASSWORD, "newPassword": PASSWORD}, "newPassword"),
            ({"currentPassword": PASSWORD, "newPassword": "short"}, "newPassword"),
            ({"currentPassword": PASSWORD}, "newPassword"),
        ]
        for body, key in cases:
            res = self.put_json(self.URL, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(key, res.json()["details"], body)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_rate_limit(self):
        for _ in range(10):
            self.put_json(self.URL, {"currentPassword": "wrong", "newPassword": NEW_PASSWORD})
        res = self.put_json(self.URL, {"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (429, "RATE_LIMITED"))


class WithdrawTests(MeTestCase):
    def withdraw(self, password=PASSWORD):
        with self.captureOnCommitCallbacks(execute=True):
            return self.delete_json(ME_URL, {"currentPassword": password})

    def test_withdraw(self):
        self.user.addresses.create(recipient_name="山田 太郎", postal_code="100-0001", prefecture=self.prefecture,
                                   city="千代田区", address_line1="1-1", phone="0312345678", is_default=True)
        product = make_product(make_producer(business_name="ほかの農園"))
        CartItem.objects.create(user=self.user, product=product, quantity=1)
        FavoriteProduct.objects.create(user=self.user, product=product)
        finished = make_order(user=self.user)
        add_shipment(finished, product.producer, status="delivered")
        consents = UserConsent.objects.filter(user=self.user).count()

        res = self.withdraw()
        self.assertEqual(res.status_code, 204)
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual((user.email, user.last_name, user.first_name, user.phone, user.birth_date,
                          user.prefecture_id, user.interests, user.is_active),
                         (f"deleted_{user.pk}@invalid", "退会ユーザー", "", None, None, None, [], False))
        self.assertIsNotNone(user.deleted_at)
        self.assertFalse(user.has_usable_password())
        self.assertFalse(Address.objects.exists())
        self.assertFalse(CartItem.objects.exists())
        self.assertFalse(FavoriteProduct.objects.exists())
        self.assertTrue(Order.objects.filter(pk=finished.pk).exists())         # 注文の記録は残す
        self.assertEqual(UserConsent.objects.filter(user=user).count(), consents)
        self.assertEqual(mail.outbox[0].to, ["taro@example.com"])               # 匿名化する前のアドレスへ
        self.assertEqual(self.client.get(ME_URL).status_code, 401)
        self.assertEqual(self.signin("taro@example.com").status_code, 401)

    def test_producer_is_suspended(self):
        producer = make_producer(user=self.user)
        self.assertEqual(self.withdraw().status_code, 204)
        producer.refresh_from_db()
        self.assertEqual(producer.publish_status, "suspended")

    def test_wrong_password(self):
        res = self.withdraw("wrong")
        self.assertEqual((res.status_code, set(res.json()["details"])), (400, {"currentPassword"}))
        self.assertTrue(User.objects.get(pk=self.user.pk).is_active)

    def test_staff_cannot_withdraw(self):
        User.objects.filter(pk=self.user.pk).update(is_staff=True)
        self.assertEqual(self.withdraw().status_code, 403)

    def assert_blocked(self, text):
        res = self.withdraw()
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "ACTIVE_TRANSACTIONS_EXIST"))
        self.assertIn(text, res.json()["errorMsg"])
        self.assertTrue(User.objects.get(pk=self.user.pk).is_active)

    def test_blocked_by_orders(self):
        producer = make_producer(business_name="ほかの農園")
        make_order(user=self.user, payment_status="pending")
        self.assert_blocked("お支払い待ちの注文")
        Order.objects.update(payment_status="failed")
        add_shipment(make_order(user=self.user), producer, status="cancel_requested")
        self.assert_blocked("発送前・キャンセル申請中の注文")

    def test_blocked_as_producer(self):
        producer = make_producer(user=self.user)
        add_shipment(make_order(user=make_user(email="buyer@example.com")), producer)
        self.assert_blocked("生産者として発送前")

    def experience_slot(self, producer, start):
        experience = Experience.objects.create(
            producer=producer, prefecture=self.prefecture, title="収穫体験", description="説明", place="畑",
            price_adult=3000, family_ok=True, beginner_ok=True, cancel_policy="前日まで", publish_status="public")
        return ExperienceSlot.objects.create(experience=experience, start_at=start, duration_min=120, capacity=10,
                                             reserved_count=2, status="open")

    def reserve(self, user, slot, status="confirmed"):
        return Reservation.objects.create(
            reservation_no=f"R-{Reservation.objects.count() + 1}", slot=slot, user=user, adult_count=2,
            child_count=0, infant_count=0, representative_name="山田 太郎", phone="09012345678",
            total_amount=6000, status=status, policy_agreed_at=timezone.now())

    def test_blocked_by_reservations(self):
        producer = make_producer(business_name="ほかの農園")
        past = self.experience_slot(producer, timezone.now() - timedelta(days=1))
        self.reserve(self.user, past)                                   # 終わった予約は数えない
        future = self.experience_slot(producer, timezone.now() + timedelta(days=3))
        self.reserve(self.user, future, status="canceled")              # キャンセル済みも数えない
        self.reserve(self.user, future)
        self.assert_blocked("これからの体験予約")

    def test_blocked_by_reservations_on_my_experience(self):
        producer = make_producer(user=self.user)
        slot = self.experience_slot(producer, timezone.now() + timedelta(days=3))
        self.reserve(make_user(email="guest@example.com"), slot)
        self.assert_blocked("あなたの体験のこれからの予約")

    def job(self, producer):
        return Job.objects.create(
            producer=producer, prefecture=self.prefecture, title="収穫スタッフ", term_type="one_day",
            pay_unit="daily", pay_amount=10000, work_hours="8:00〜15:00", work_place="畑", slots=3,
            description="収穫", inexperienced_ok=True, publish_status="public")

    def test_blocked_by_job_applications(self):
        job = self.job(make_producer(business_name="ほかの農園"))
        JobApplication.objects.create(job=job, user=self.user, status="screening")
        self.assert_blocked("選考中の求人応募")

    def test_blocked_by_applications_to_my_job(self):
        job = self.job(make_producer(user=self.user))
        JobApplication.objects.create(job=job, user=make_user(email="worker@example.com"), status="applied")
        self.assert_blocked("あなたの求人への選考中の応募")

    def test_rate_limit(self):
        for _ in range(10):
            self.withdraw("wrong")
        self.assertEqual(self.withdraw().status_code, 429)
        self.assertEqual(self.client.get(ME_URL).status_code, 200)       # 取得は回数制限の対象外
