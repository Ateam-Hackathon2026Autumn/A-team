"""ストーリー管理（学ぶページ）

認証: 生産者（承認済み）。取得は掲載停止中でもできる
仕様: api-spec.md「7. 実装で決めたこと」ステップ13。ER図の producer_stories の形（Notion の title・category は使わない）

実装済み:
  - ストーリー取得: GET /api/v1/dashboard/story
      ・{craft, method, process, environment, reason, goal, publishStatus, updatedAt}
      ・行は承認時に作ってある。なければ 404 にせず空の内容（すべて null・draft・updatedAt null）
  - ストーリー保存: PUT /api/v1/dashboard/story
      ・7項目すべて送って置き換える（本文は null か2,000文字まで。空なら null）。行がなければ作る。作ったときも 200
      ・公開（public）には本文が1項目以上（足りなければ 400 details.publishStatus）
      ・生産者が掲載停止中 → 409 PRODUCER_SUSPENDED／運営がストーリーを停止中 → 409 STORY_SUSPENDED
      ・農園が非公開でも public にしておける（お客さんに見えるのは農園も公開中のとき。services/visibility.py）
"""
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Producer, ProducerStory, PublishStatus

from ...common.exceptions import Conflict
from ...common.permissions import IsApprovedProducer, ensure_producer_not_suspended
from ...serializers.dashboard.story import DashboardStorySerializer, StoryPutSerializer, empty_story


class DashboardStoryView(APIView):
    """GET・PUT /api/v1/dashboard/story"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        story = ProducerStory.objects.filter(producer=request.user.producer).first()
        if story is None:
            return Response(DashboardStorySerializer(empty_story()).data)
        return Response(DashboardStorySerializer(story).data)

    def put(self, request):
        serializer = StoryPutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            producer = Producer.objects.select_for_update().get(pk=request.user.producer.pk)
            ensure_producer_not_suspended(producer)
            story, _ = ProducerStory.objects.select_for_update().get_or_create(producer=producer)
            if story.publish_status == PublishStatus.SUSPENDED:
                raise Conflict("STORY_SUSPENDED", "このストーリーは運営により掲載停止中です。運営にお問い合わせください。")
            for field, value in serializer.validated_data.items():
                setattr(story, field, value)
            story.save()
        return Response(DashboardStorySerializer(story).data)
