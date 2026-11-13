"""生産者プロフィール のテスト

テスト対象: api/views/dashboard/profile.py
  - 生産者プロフィール取得: GET /api/v1/dashboard/profile
  - 生産者プロフィール更新: PATCH /api/v1/dashboard/profile
      ・送った項目だけ。事業者名・代表者名・ジャンルは400。画像は自分のアップロードだけ。農園画像は置き換え
      ・掲載停止中は公開状態だけ変えられない（409）
"""
from django.utils import timezone

from marche.models import Producer, ProducerImage, ProducerStory, PublishStatus

from ..public.test_uploads import image_file
from ..utils import ApiTestCase, make_prefecture, make_producer, make_user

URL = "/api/v1/dashboard/profile"


class ProfileTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園", career_start_year=2023)
        self.signin(self.producer.user.email)

    def upload(self):
        return self.post_multipart("/api/v1/uploads/images", {"image": image_file()}).json()["key"]

    def test_get(self):
        ProducerStory.objects.create(producer=self.producer, reason="祖父の畑", goal="担い手を増やす")
        ProducerImage.objects.create(producer=self.producer, image="images/x/b.jpg", sort_order=1)
        first = ProducerImage.objects.create(producer=self.producer, image="images/x/a.jpg", sort_order=0)
        with self.assertNumQueries(5):  # 生産者の確認（セッション・ユーザー・生産者）＋生産者とストーリー・画像
            data = self.client.get(URL).json()
        self.assertEqual(data["businessName"], "山田農園")
        self.assertEqual((data["careerStartYear"], data["profileImage"], data["profileImageUrl"]), (2023, None, None))
        self.assertEqual(data["images"][0]["id"], first.id)
        self.assertEqual((data["images"][0]["key"], data["images"][0]["sortOrder"]), ("images/x/a.jpg", 0))
        self.assertEqual((data["reason"], data["goal"], data["storyPublishStatus"]), ("祖父の畑", "担い手を増やす", "draft"))
        self.assertEqual((data["approvalStatus"], data["publishStatus"]), ("approved", "public"))

    def test_get_without_story(self):
        data = self.client.get(URL).json()
        self.assertEqual((data["reason"], data["goal"], data["storyPublishStatus"], data["images"]),
                         (None, None, None, []))

    def test_update(self):
        osaka = make_prefecture(pk=27, name="大阪府")
        cover, a, b = self.upload(), self.upload(), self.upload()
        res = self.patch_json(URL, {"prefectureId": osaka.id, "city": " 堺市 ", "intro": "新しい紹介",
                                    "careerStartYear": None, "foundedYear": 1962, "acceptsExperience": True,
                                    "coverImage": cover, "imageKeys": [b, a], "publishStatus": "private"})
        self.assertEqual(res.status_code, 200, res.json())
        data = res.json()
        self.assertEqual((data["prefectureId"], data["city"], data["intro"], data["careerStartYear"],
                          data["foundedYear"], data["acceptsExperience"], data["coverImage"], data["publishStatus"]),
                         (27, "堺市", "新しい紹介", None, 1962, True, cover, "private"))
        self.assertTrue(data["coverImageUrl"].endswith(cover))
        self.assertEqual([(i["key"], i["sortOrder"]) for i in data["images"]], [(b, 0), (a, 1)])
        self.assertEqual(data["productionItems"], "野菜")                       # 送らなかった項目はそのまま
        res = self.patch_json(URL, {"imageKeys": [], "coverImage": None, "publishStatus": "public"})
        self.assertEqual((res.json()["images"], res.json()["coverImage"], res.json()["publishStatus"]), ([], None, "public"))
        self.assertFalse(ProducerImage.objects.exists())

    def test_validation(self):
        theirs = "images/999999/x.jpg"
        cases = [({}, "nonFieldErrors"), ({"businessName": "別名"}, "businessName"),
                 ({"representativeName": "別人"}, "representativeName"), ({"genre": "fishery"}, "genre"),
                 ({"city": ""}, "city"), ({"city": "あ" * 51}, "city"), ({"intro": " "}, "intro"),
                 ({"productionItems": "あ" * 101}, "productionItems"), ({"prefectureId": 99}, "prefectureId"),
                 ({"foundedYear": timezone.localdate().year + 1}, "foundedYear"),
                 ({"publishStatus": "draft"}, "publishStatus"), ({"publishStatus": "suspended"}, "publishStatus"),
                 ({"profileImage": theirs}, "profileImage"), ({"imageKeys": [theirs]}, "imageKeys"),
                 ({"imageKeys": ["a"] * 11}, "imageKeys"), ({"reason": "理由"}, "reason"),
                 ({"approvalStatus": "approved"}, "approvalStatus")]
        key = self.upload()
        cases.append(({"imageKeys": [key, key]}, "imageKeys"))
        for body, field in cases:
            res = self.patch_json(URL, body)
            self.assertEqual(res.status_code, 400, body)
            self.assertIn(field, res.json()["details"], body)
        self.assertEqual(Producer.objects.get().city, "八王子市")

    def test_suspended(self):
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        res = self.patch_json(URL, {"publishStatus": "public", "city": "町田市"})
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCER_SUSPENDED"))
        self.assertEqual(Producer.objects.get().city, "八王子市")
        res = self.patch_json(URL, {"city": "町田市"})                            # ほかの項目は変えられる
        self.assertEqual((res.status_code, res.json()["publishStatus"]), (200, "suspended"))

    def test_permission(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.signin(make_user(email="buyer@example.com").email)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.patch_json(URL, {"city": "x"}).status_code, 403)
