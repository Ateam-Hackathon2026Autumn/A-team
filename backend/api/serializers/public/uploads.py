"""画像アップロード のシリアライザー

使う view: api/views/public/uploads.py
- リクエスト: multipart/form-data の image（ファイル1つ）。それ以外の項目は 400
- レスポンス: {key, url}（key は商品などの登録APIに渡す。url はプレビュー用）
"""
from rest_framework import serializers

from ...common.serializers import StrictSerializer


class ImageUploadSerializer(StrictSerializer):
    image = serializers.FileField(error_messages={"required": "画像を選んでください。",
                                                  "invalid": "画像を選んでください。",
                                                  "empty": "空のファイルはアップロードできません。"})


class ImageUploadResponseSerializer(serializers.Serializer):
    key = serializers.CharField()
    url = serializers.CharField()
