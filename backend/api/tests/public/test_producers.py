"""生産者・学ぶ（公開側） のテスト

テスト対象: api/views/public/producers.py
  - 生産者一覧: GET /api/v1/producers
  - 生産者プロフィール: GET /api/v1/producers/:producerId
  - 生産者ストーリー: GET /api/v1/producers/:producerId/story
バッジの判定（services/badges.py）もここで確かめる。S3 には接続しない（ApiTestCase）。
"""
from datetime import timedelta

from django.utils import timezone

from marche.models import FavoriteProducer, Producer, ProducerImage, ProducerStory, PublishStatus

from ...services.badges import badges_for
from ..utils import ApiTestCase, make_prefecture, make_producer, make_user

LIST_URL = "/api/v1/producers"


def profile_url(producer_id):
    return f"/api/v1/producers/{producer_id}"


def story_url(producer_id):
    return f"/api/v1/producers/{producer_id}/story"


def ids(response):
    return [item["id"] for item in response.json()["items"]]


def add_story(producer, publish_status=PublishStatus.PUBLIC, **fields):
    defaults = dict(craft="土づくりにこだわっています", method="無農薬で育てています", process="", environment=None,
                    reason="祖父の畑を継ぎたくて", goal="地域の野菜を全国へ")
    defaults.update(fields)
    return ProducerStory.objects.create(producer=producer, publish_status=publish_status, **defaults)


# =========================================================
# バッジ
# =========================================================

class BadgeTests(ApiTestCase):
    def test_badges(self):
        now = timezone.now()
        this_year = timezone.localdate(now).year
        cases = [
            (dict(career_start_year=this_year - 5), ["new_farmer"]),
            (dict(career_start_year=this_year), ["new_farmer"]),
            (dict(career_start_year=this_year - 6), []),
            (dict(career_start_year=this_year + 1), []),  # 未来の年は対象外
            (dict(approved_at=now - timedelta(days=29)), ["new_participant"]),
            (dict(approved_at=now - timedelta(days=30)), []),  # 30日ちょうどは含めない
            (dict(approved_at=now + timedelta(days=1)), []),  # 未来の日時は対象外
            (dict(accepts_experience=True, recruiting=True, career_start_year=this_year,
                  approved_at=now - timedelta(days=1)),
             ["new_farmer", "new_participant", "accepts_experience", "recruiting"]),
        ]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                producer = Producer(**{"accepts_experience": False, "recruiting": False, **fields})
                self.assertEqual(badges_for(producer, now), expected)


# =========================================================
# 生産者一覧
# =========================================================

class ProducerListTests(ApiTestCase):
    def test_item_shape(self):
        producer = make_producer(business_name="山田農園", career_start_year=timezone.localdate().year - 1,
                                 founded_year=1962, accepts_experience=True, profile_image="images/1/face.jpg")
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["total"], body["page"], body["pageSize"], body["totalPages"]), (1, 1, 20, 1))
        self.assertEqual(body["items"][0], {
            "id": producer.id, "businessName": "山田農園", "genre": "agriculture", "prefectureId": 13,
            "prefectureName": "東京都", "city": "八王子市", "productionItems": "野菜",
            "profileImageUrl": "/media/images/1/face.jpg", "coverImageUrl": None,
            "careerStartYear": producer.career_start_year, "foundedYear": 1962, "acceptsExperience": True,
            "recruiting": False, "badges": ["new_farmer", "accepts_experience"], "hasPublicStory": False,
            "isFavorited": False,
        })

    def test_only_public(self):
        visible = make_producer()
        make_producer(approval=Producer.ApprovalStatus.PENDING)
        make_producer(publish=PublishStatus.PRIVATE)
        make_producer(publish=PublishStatus.SUSPENDED)
        stopped = make_producer()
        stopped.user.is_active = False
        stopped.user.save()
        withdrawn = make_producer()
        withdrawn.user.deleted_at = timezone.now()
        withdrawn.user.save()
        self.assertEqual(ids(self.client.get(LIST_URL)), [visible.id])

    def test_filters(self):
        this_year = timezone.localdate().year
        osaka = make_prefecture(pk=27, name="大阪府")
        farmer = make_producer(career_start_year=this_year - 2, featured_score=10)
        fisher = make_producer(genre=Producer.Genre.FISHERY, prefecture=osaka)
        veteran = make_producer(career_start_year=this_year - 20, featured_score="0.50")
        add_story(veteran)
        add_story(fisher, publish_status=PublishStatus.DRAFT)

        def filtered(**params):
            return sorted(ids(self.client.get(LIST_URL, params)))

        self.assertEqual(filtered(featured="true"), sorted([farmer.id, veteran.id]))
        self.assertEqual(filtered(newFarmer="true"), [farmer.id])
        self.assertEqual(filtered(hasStory="true"), [veteran.id])
        self.assertEqual(filtered(genre="fishery"), [fisher.id])
        self.assertEqual(filtered(prefectureId=27), [fisher.id])
        self.assertEqual(filtered(prefectureId=99), [])
        self.assertEqual(filtered(featured="true", newFarmer="true"), [farmer.id])
        self.assertEqual(len(filtered(featured="false", newFarmer="false")), 3)  # false は絞り込みなし

    def test_sort_orders(self):
        now = timezone.now()
        old = make_producer(approved_at=now - timedelta(days=100), featured_score=5)
        new = make_producer(approved_at=now - timedelta(days=1), featured_score=1)
        no_date = make_producer(featured_score=5)
        self.assertEqual(ids(self.client.get(LIST_URL)), [new.id, old.id, no_date.id])  # newest・null は末尾
        self.assertEqual(ids(self.client.get(LIST_URL, {"sort": "featured"})), [no_date.id, old.id, new.id])

    def test_has_public_story_and_is_favorited(self):
        with_story = make_producer()
        add_story(with_story)
        liked = make_producer()
        user = make_user(email="buyer@example.com")
        FavoriteProducer.objects.create(user=user, producer=liked)
        self.signin(user.email)
        items = {item["id"]: (item["hasPublicStory"], item["isFavorited"])
                 for item in self.client.get(LIST_URL).json()["items"]}
        self.assertEqual(items, {with_story.id: (True, False), liked.id: (False, True)})

    def test_invalid_query_is_400(self):
        bad = ["?featured=1", "?featured=True", "?newFarmer=yes", "?hasStory=", "?genre=forestry",
               "?prefectureId=0", "?prefectureId=abc", "?sort=popular", "?foo=1", "?sort=newest&sort=featured",
               "?pageSize=101"]
        for query in bad:
            with self.subTest(query=query):
                res = self.client.get(LIST_URL + query)
                self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "VALIDATION_ERROR"))

    def test_query_count(self):
        for _ in range(5):
            add_story(make_producer())
        with self.assertNumQueries(4):  # 件数・一覧（都道府県を JOIN、サブクエリ）＋SAVEPOINT・RELEASE
            self.client.get(LIST_URL, {"hasStory": "true"})


# =========================================================
# 生産者プロフィール
# =========================================================

class ProducerProfileTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")

    def test_profile(self):
        second = ProducerImage.objects.create(producer=self.producer, image="images/1/b.jpg", sort_order=1)
        first = ProducerImage.objects.create(producer=self.producer, image="images/1/a.jpg", sort_order=0)
        add_story(self.producer)
        res = self.client.get(profile_url(self.producer.id))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["representativeName"], body["intro"]), ("山田 太郎", "季節の野菜を育てています"))
        self.assertEqual(body["images"], [{"id": first.id, "url": "/media/images/1/a.jpg", "sortOrder": 0},
                                          {"id": second.id, "url": "/media/images/1/b.jpg", "sortOrder": 1}])
        self.assertEqual((body["craft"], body["reason"], body["goal"]),
                         ("土づくりにこだわっています", "祖父の畑を継ぎたくて", "地域の野菜を全国へ"))
        self.assertTrue(body["hasPublicStory"])
        for private in ["userId", "featuredScore", "stripeAccountId", "approvalStatus", "phone", "email"]:
            self.assertNotIn(private, body)

    def test_support_block_is_null_unless_story_is_public(self):
        url = profile_url(self.producer.id)
        body = self.client.get(url).json()
        self.assertEqual((body["craft"], body["reason"], body["goal"], body["images"]), (None, None, None, []))
        add_story(self.producer, publish_status=PublishStatus.SUSPENDED)
        body = self.client.get(url).json()
        self.assertEqual((body["craft"], body["hasPublicStory"]), (None, False))

    def test_not_public_is_404(self):
        hidden = make_producer(publish=PublishStatus.PRIVATE)
        # 本人がログインしていても公開側では見られない
        self.signin(hidden.user.email)
        for producer_id in [hidden.id, 999999, 2 ** 63]:
            res = self.client.get(profile_url(producer_id))
            self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "PRODUCER_NOT_FOUND"))
        res = self.client.get("/api/v1/producers/abc")
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "NOT_FOUND"))

    def test_unknown_query_is_400_and_query_count(self):
        self.assertEqual(self.client.get(profile_url(self.producer.id), {"foo": 1}).status_code, 400)
        ProducerImage.objects.create(producer=self.producer, image="images/1/a.jpg", sort_order=0)
        add_story(self.producer)
        with self.assertNumQueries(4):  # 生産者（都道府県・ストーリーを JOIN）・農園画像＋SAVEPOINT・RELEASE
            self.client.get(profile_url(self.producer.id))


# =========================================================
# 生産者ストーリー
# =========================================================

class ProducerStoryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer(business_name="山田農園")

    def test_story(self):
        story = add_story(self.producer)
        res = self.client.get(story_url(self.producer.id))
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["id"], story.id)
        self.assertEqual(body["producerId"], self.producer.id)
        self.assertEqual((body["craft"], body["method"], body["process"], body["environment"]),
                         ("土づくりにこだわっています", "無農薬で育てています", None, None))  # 空は null
        self.assertEqual(body["producer"]["businessName"], "山田農園")
        self.assertTrue(body["producer"]["hasPublicStory"])
        self.assertIn("updatedAt", body)
        self.assertNotIn("category", body)

    def test_not_public_is_404(self):
        url = story_url(self.producer.id)
        res = self.client.get(url)  # ストーリーなし
        self.assertEqual((res.status_code, res.json()["errorCode"]), (404, "STORY_NOT_FOUND"))
        story = add_story(self.producer, publish_status=PublishStatus.DRAFT)
        for publish_status in [PublishStatus.DRAFT, PublishStatus.PRIVATE, PublishStatus.SUSPENDED]:
            story.publish_status = publish_status
            story.save()
            with self.subTest(publish_status=publish_status):
                self.assertEqual(self.client.get(url).json()["errorCode"], "STORY_NOT_FOUND")
        story.publish_status = PublishStatus.PUBLIC
        story.save()
        self.producer.publish_status = PublishStatus.SUSPENDED  # 生産者が掲載停止ならストーリーも出さない
        self.producer.save()
        self.assertEqual(self.client.get(url).json()["errorCode"], "STORY_NOT_FOUND")
        self.assertEqual(self.client.get(story_url(999999)).status_code, 404)

    def test_unknown_query_is_400(self):
        add_story(self.producer)
        self.assertEqual(self.client.get(story_url(self.producer.id), {"foo": 1}).status_code, 400)
