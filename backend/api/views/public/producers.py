"""生産者・学ぶ（公開側）

認証: 公開（ログイン不要。ログイン中ならお気に入り済みを返す）
仕様: Notion の各API定義＋api-spec.md「7. 実装で決めたこと」ステップ3。カラム名: claude/er-diagram.md

このファイルの API（シーケンス図は Notion の「学ぶ・生産者プロフィール・ストーリー詳細」）:
    - 生産者一覧: GET /api/v1/producers
        ・公開条件は services/visibility.py（承認済み・公開中・ユーザーが有効で未退会）
        ・featured=true（featured_score > 0）・newFarmer=true（就業5年以内）・hasStory=true（公開中のストーリーあり）
          ・genre・prefectureId で絞り込み（すべて AND。存在しない prefectureId は 200 の空配列）
        ・sort: newest（初期値・approved_at の降順、null は末尾）/ featured（featured_score の降順）。どちらも最後に id DESC
        ・badges は services/badges.py。has_public_story・is_favorited は EXISTS のサブクエリ（N+1 にしない）
    - 生産者プロフィール: GET /api/v1/producers/:producerId
        ・カードの項目＋代表者名・紹介・農園画像（sort_order・id の昇順）・応援ブロック（craft・reason・goal）
        ・公開対象外・存在しないは区別せず 404 PRODUCER_NOT_FOUND
    - 生産者ストーリー: GET /api/v1/producers/:producerId/story
        ・producer_stories が public のときだけ。生産者が公開対象外でも同じ 404 STORY_NOT_FOUND

未知のクエリパラメーターは 400（どのAPIも）。数字でない ID は URL に一致しないので共通の 404 NOT_FOUND。
"""
from django.db import transaction
from django.db.models import BooleanField, Exists, F, OuterRef, Prefetch, Value
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import FavoriteProducer, ProducerImage, ProducerStory, PublishStatus

from ...common.exceptions import ApiError
from ...common.pagination import paginate, validate_query
from ...common.serializers import QuerySerializer
from ...serializers.public.producers import (
    MAX_ID,
    ProducerListQuerySerializer,
    ProducerProfileSerializer,
    ProducerStorySerializer,
    PublicProducerSerializer,
)
from ...services.badges import new_farmer_years
from ...services.visibility import public_producers

SORT_ORDERS = {
    "newest": [F("approved_at").desc(nulls_last=True), "-id"],
    "featured": ["-featured_score", "-id"],
}


def public_story_exists():
    return Exists(ProducerStory.objects.filter(producer=OuterRef("pk"), publish_status=PublishStatus.PUBLIC))


def annotate_producers(queryset, user):
    """生産者カードに必要な項目を1本の SQL で取る（都道府県は JOIN、ストーリーの有無・お気に入りはサブクエリ）"""
    if user.is_authenticated:
        is_favorited = Exists(FavoriteProducer.objects.filter(user=user, producer=OuterRef("pk")))
    else:
        is_favorited = Value(False, output_field=BooleanField())
    return queryset.select_related("prefecture").annotate(
        has_public_story=public_story_exists(), is_favorited=is_favorited)


class ProducerListView(APIView):
    """GET /api/v1/producers"""

    permission_classes = [AllowAny]

    def get(self, request):
        query = validate_query(ProducerListQuerySerializer, request)
        now = timezone.now()
        producers = public_producers()
        if query.get("featured"):
            producers = producers.filter(featured_score__gt=0)
        if query.get("new_farmer"):
            oldest, this_year = new_farmer_years(timezone.localdate(now))
            producers = producers.filter(career_start_year__gte=oldest, career_start_year__lte=this_year)
        if query.get("has_story"):
            producers = producers.filter(public_story_exists())
        if "genre" in query:
            producers = producers.filter(genre=query["genre"])
        if "prefecture_id" in query:
            producers = producers.filter(prefecture_id=query["prefecture_id"])

        listed = annotate_producers(producers, request.user).order_by(*SORT_ORDERS[query["sort"]])
        return Response(paginate(listed, query, PublicProducerSerializer, context={"now": now},
                                 count_queryset=producers))


def find_public_producer(request, producer_id):
    """公開中の生産者（注釈・ストーリー付き）。いなければ None"""
    if producer_id > MAX_ID:
        return None
    return annotate_producers(public_producers(), request.user).select_related("story").filter(pk=producer_id).first()


class ProducerProfileView(APIView):
    """GET /api/v1/producers/:producerId"""

    permission_classes = [AllowAny]

    def get(self, request, producer_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        with transaction.atomic():  # 生産者・画像・ストーリーを同じ時点で読む
            producer = None
            if producer_id <= MAX_ID:
                images = ProducerImage.objects.order_by("sort_order", "id")
                producer = (
                    annotate_producers(public_producers(), request.user)
                    .select_related("story").prefetch_related(Prefetch("producer_images", queryset=images))
                    .filter(pk=producer_id).first()
                )
            if producer is None:
                raise ApiError(status.HTTP_404_NOT_FOUND, "PRODUCER_NOT_FOUND", "生産者が見つかりません。")
            data = ProducerProfileSerializer(producer, context={"now": timezone.now()}).data
        return Response(data)


class ProducerStoryView(APIView):
    """GET /api/v1/producers/:producerId/story"""

    permission_classes = [AllowAny]

    def get(self, request, producer_id):
        validate_query(QuerySerializer, request)  # クエリパラメーターは受け付けない
        producer = find_public_producer(request, producer_id)
        story = getattr(producer, "story", None) if producer else None
        if story is None or story.publish_status != PublishStatus.PUBLIC:
            # 生産者が公開対象外・ストーリーがない・下書きを区別しない（下書きの有無を知られないため）
            raise ApiError(status.HTTP_404_NOT_FOUND, "STORY_NOT_FOUND", "ストーリーが見つかりません。")
        story.producer = producer  # 注釈付きの生産者を使う
        return Response(ProducerStorySerializer(story, context={"now": timezone.now()}).data)
