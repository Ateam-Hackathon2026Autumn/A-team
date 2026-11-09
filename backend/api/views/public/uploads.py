"""画像アップロード

認証: 会員（ログイン必須。データを変えるので CSRF も確認する）
仕様: api-spec.md「ファイル」＋「7. 実装で決めたこと」（Notion には定義なし）

このファイルの API:
    - 画像アップロード: POST /api/v1/uploads/images
        ・multipart/form-data の image。jpg・png だけ（中身で判定）、5MB まで
        ・位置情報などのメタデータを消してから images/{user_id}/ランダム に保存 → services/storage.py
        ・201 で {key, url}。DB には書かない（キーを受け取る商品登録などのAPIで「自分の画像か」を確かめる）
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...common.images import image_url
from ...serializers.public.uploads import ImageUploadResponseSerializer, ImageUploadSerializer
from ...services.storage import save_public_image


class ImageUploadView(APIView):
    """POST /api/v1/uploads/images"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = {key: request.data[key] for key in request.data}  # QueryDict → dict（未知の項目は 400 にする）
        serializer = ImageUploadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        key = save_public_image(request.user, serializer.validated_data["image"])
        body = ImageUploadResponseSerializer({"key": key, "url": image_url(key)}).data
        return Response(body, status=status.HTTP_201_CREATED)
