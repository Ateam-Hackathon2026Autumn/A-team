"""通報

認証: 会員（未ログインは 401）。メール未確認でも使える
仕様: api-spec.md「7. 実装で決めたこと」ステップ12。シーケンス図は Notion「問い合わせ・通報」

実装済み:
  - 通報: POST /api/v1/reports
      ・{targetType, targetId, reason, detail（任意・1,000文字まで）}。reason は serializers/public/reports.py の6種類
      ・targetType は product・experience・job・producer（公開中のものだけ。ないもの・非公開は 404 TARGET_NOT_FOUND）
        story・user は今は 400（user はチャットと一緒に作る）
      ・自分の商品・体験・求人・農園は 409 CANNOT_REPORT_OWN
      ・同じ対象を何度でも通報できる。status=open で作る。通報した人へのメールはなし。201 で {id}
      ・同じ会員は1時間10回まで（429 RATE_LIMITED）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from marche.models import Experience, Job, Product, Report

from ...common.exceptions import ApiError, Conflict
from ...serializers.public.reports import ReportCreateSerializer
from ...services.visibility import public_content, public_producers

TARGETS = {
    Report.TargetType.PRODUCT: (lambda: public_content(Product.objects.all()), "producer__user_id"),
    Report.TargetType.EXPERIENCE: (lambda: public_content(Experience.objects.all()), "producer__user_id"),
    Report.TargetType.JOB: (lambda: public_content(Job.objects.all()), "producer__user_id"),
    Report.TargetType.PRODUCER: (public_producers, "user_id"),
}


class ReportThrottle(UserRateThrottle):
    """同じ会員は1時間10回まで"""

    scope = "report"


class ReportCreateView(APIView):
    """POST /api/v1/reports"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ReportThrottle]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset, owner_field = TARGETS[data["target_type"]]
        owner_id = queryset().filter(pk=data["target_id"]).values_list(owner_field, flat=True).first()
        if owner_id is None:
            raise ApiError(status.HTTP_404_NOT_FOUND, "TARGET_NOT_FOUND", "通報する対象が見つかりません。")
        if owner_id == request.user.pk:
            raise Conflict("CANNOT_REPORT_OWN", "ご自身の掲載内容は通報できません。")
        report = Report.objects.create(
            reporter=request.user, target_type=data["target_type"], target_id=data["target_id"],
            reason=data["reason"], detail=data.get("detail"), status=Report.Status.OPEN)
        return Response({"id": report.id}, status=status.HTTP_201_CREATED)
