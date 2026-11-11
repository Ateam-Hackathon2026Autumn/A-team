"""問い合わせ

認証: ゲスト可（CSRF は未ログインでも確認する。api/common/authentication.py）
仕様: api-spec.md「7. 実装で決めたこと」ステップ12。シーケンス図は Notion「問い合わせ・通報」

実装済み:
  - 問い合わせ送信: POST /api/v1/inquiries
      ・{category, subject（100文字まで）, body（5,000文字まで）, email（ゲストだけ必須）, orderId（任意）}
      ・会員は登録のメールアドレスを返信先にする。orderId は会員の自分の注文だけ（ほかは 400）
      ・status=open・priority=medium で作る（優先度は運営が管理画面で変える）
      ・返信先に受付メール（件名・本文の控えつき）。201 で {id, category, subject, createdAt}
      ・同じIPから1時間5回まで（429 RATE_LIMITED）。メール確認済みは求めない
"""
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Inquiry

from ...common.throttles import IPRateThrottle
from ...serializers.public.inquiries import InquiryCreateSerializer, InquirySerializer
from ...services import mail


class InquiryCreateView(APIView):
    """POST /api/v1/inquiries"""

    permission_classes = [AllowAny]
    throttle_classes = [IPRateThrottle]
    throttle_scope = "inquiry"

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        serializer = InquiryCreateSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            inquiry = Inquiry.objects.create(
                user=user, order=data.get("order"), email=user.email if user else data["email"],
                category=data["category"], subject=data["subject"], body=data["body"],
                status=Inquiry.Status.OPEN, priority=Inquiry.Priority.MEDIUM)
            name = f"{user.last_name} {user.first_name}".strip() if user else ""
            transaction.on_commit(lambda: mail.send_inquiry_received(inquiry, name))
        return Response(InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)
