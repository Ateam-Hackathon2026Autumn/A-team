"""ストーリー管理（学ぶページ） のテスト

テスト対象: api/views/dashboard/story.py
  - ストーリー取得: GET /api/v1/dashboard/story（行がなければ空の内容）
  - ストーリー保存: PUT /api/v1/dashboard/story（7項目を置き換え。公開には本文1項目以上。停止中は409）
"""
from marche.models import ProducerStory, PublishStatus

from ..utils import ApiTestCase, make_producer, make_user

URL = "/api/v1/dashboard/story"
EMPTY = {"craft": None, "method": None, "process": None, "environment": None, "reason": None, "goal": None}


def body(**kw):
    return {**EMPTY, "publishStatus": "draft", **kw}


class StoryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.producer = make_producer()
        self.signin(self.producer.user.email)

    def test_get_without_row(self):
        self.assertEqual(self.client.get(URL).json(), {**EMPTY, "publishStatus": "draft", "updatedAt": None})

    def test_put_creates_and_replaces(self):
        res = self.put_json(URL, body(craft=" 減農薬です ", reason="祖父の畑を継ぐため", publishStatus="public"))
        self.assertEqual(res.status_code, 200, res.json())
        self.assertEqual((res.json()["craft"], res.json()["reason"], res.json()["publishStatus"]),
                         ("減農薬です", "祖父の畑を継ぐため", "public"))
        story = ProducerStory.objects.get(producer=self.producer)
        res = self.put_json(URL, body(goal="担い手を増やす", craft=""))   # 送らなかった値は消える（置き換え）
        self.assertEqual(res.json(), {**EMPTY, "goal": "担い手を増やす", "publishStatus": "draft",
                                      "updatedAt": res.json()["updatedAt"]})
        self.assertEqual(ProducerStory.objects.get().pk, story.pk)
        self.assertEqual(self.client.get(URL).json()["goal"], "担い手を増やす")
        public = self.client.get(f"/api/v1/producers/{self.producer.id}/story")
        self.assertEqual(public.status_code, 404)  # 下書きは公開側に出ない

    def test_validation(self):
        for data, key in [(body(publishStatus="public"), "publishStatus"),
                          (body(publishStatus="public", craft="  "), "publishStatus"),
                          (body(publishStatus="suspended"), "publishStatus"),
                          (body(method="あ" * 2001), "method"),
                          ({k: v for k, v in body().items() if k != "goal"}, "goal"),
                          (body(title="題名"), "title")]:
            res = self.put_json(URL, data)
            self.assertEqual(res.status_code, 400, data)
            self.assertIn(key, res.json()["details"], data)
        self.assertFalse(ProducerStory.objects.exists())

    def test_suspended(self):
        ProducerStory.objects.create(producer=self.producer, craft="x", publish_status=PublishStatus.SUSPENDED)
        res = self.put_json(URL, body(craft="直しました"))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "STORY_SUSPENDED"))
        self.producer.publish_status = PublishStatus.SUSPENDED
        self.producer.save()
        res = self.put_json(URL, body(craft="直しました"))
        self.assertEqual((res.status_code, res.json()["errorCode"]), (409, "PRODUCER_SUSPENDED"))
        self.assertEqual(self.client.get(URL).json()["craft"], "x")   # 取得はできる

    def test_permission(self):
        self.post_json("/api/v1/auth/signout")
        self.assertEqual(self.client.get(URL).status_code, 401)
        self.signin(make_user(email="buyer@example.com").email)
        self.assertEqual(self.put_json(URL, body()).status_code, 403)
