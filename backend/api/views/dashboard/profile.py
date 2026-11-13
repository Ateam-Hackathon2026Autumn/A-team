"""生産者プロフィール

認証: 生産者（承認済み）。掲載停止中でも取得・更新できる（公開状態の変更だけ 409 PRODUCER_SUSPENDED）
仕様: api-spec.md「7. 実装で決めたこと」ステップ13。Notion の定義（生産者プロフィール取得・更新API）から変えたところはそちら

実装済み:
  - 生産者プロフィール取得: GET /api/v1/dashboard/profile
  - 生産者プロフィール更新: PATCH /api/v1/dashboard/profile
      ・送った項目だけ変える。事業者名・代表者名・ジャンルは変えられない（問い合わせで対応）
      ・profileImage・coverImage・imageKeys は自分がアップロードした画像のキーだけ（ほかは400）。null で外せる
      ・農園画像（imageKeys）は配列で置き換え、配列の順を sort_order にする。空の配列で全部外す（S3 のファイルは消さない）
      ・publishStatus は public・private だけ。掲載停止中に送ったら 409 PRODUCER_SUSPENDED
      ・reason・goal はストーリーAPIで変える（ここでは取得だけ）
      ・ETag・If-Match は使わない。生産者の行をロックして保存し、200 で最新のプロフィール
"""
from django.db import transaction
from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Producer, ProducerImage

from ...common.permissions import IsApprovedProducer, ensure_producer_not_suspended
from ...serializers.dashboard.profile import DashboardProfileSerializer, ProfileUpdateSerializer
from ...services.storage import validate_image_keys

FIELDS = ["prefecture_id", "city", "production_items", "intro", "career_start_year", "founded_year",
          "accepts_experience", "recruiting", "profile_image", "cover_image", "publish_status"]


def load_profile(producer_id):
    images = ProducerImage.objects.order_by("sort_order", "id")
    return (Producer.objects.select_related("story").prefetch_related(Prefetch("producer_images", queryset=images))
            .get(pk=producer_id))


class DashboardProfileView(APIView):
    """GET・PATCH /api/v1/dashboard/profile"""

    permission_classes = [IsApprovedProducer]

    def get(self, request):
        return Response(DashboardProfileSerializer(load_profile(request.user.producer.pk)).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        for field in ("profile_image", "cover_image"):
            if data.get(field):
                validate_image_keys(user, [data[field]], field=field)
        if "image_keys" in data:
            validate_image_keys(user, data["image_keys"])

        with transaction.atomic():
            producer = Producer.objects.select_for_update().get(pk=user.producer.pk)
            if "publish_status" in data:
                ensure_producer_not_suspended(producer)
            for field in FIELDS:
                if field in data:
                    setattr(producer, field, data[field])
            producer.save()
            if "image_keys" in data:
                ProducerImage.objects.filter(producer=producer).delete()
                ProducerImage.objects.bulk_create([
                    ProducerImage(producer=producer, image=key, sort_order=order)
                    for order, key in enumerate(data["image_keys"])])
        return Response(DashboardProfileSerializer(load_profile(producer.pk)).data)
