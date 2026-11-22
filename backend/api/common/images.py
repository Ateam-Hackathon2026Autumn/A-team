"""画像キーを表示用URLにする

DB に保存した S3 のキー（ImageField の値、またはサブクエリで取ったキーの文字列）を、表示用のURLに変える。
- キーが空なら None
- images/ の公開画像は、設定されている場合は CloudFront の URL を返す
- 開発・テストではストレージの /media/... を返す

使い方（シリアライザー）:
    url = ImageUrlField(source="image")                  # ImageField
    thumbnail_url = ImageUrlField(source="thumbnail_key")  # サブクエリで取ったキーの文字列
"""
from urllib.parse import quote

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import serializers


def image_url(value):
    """ImageField の値かキーの文字列を受け取り、表示用URLを返す（空なら None）"""
    if not value:
        return None
    key = getattr(value, "name", value)
    if not key:
        return None
    if settings.PUBLIC_IMAGE_BASE_URL and key.startswith("images/"):
        return f"{settings.PUBLIC_IMAGE_BASE_URL}/{quote(key)}"
    return default_storage.url(key)


class ImageUrlField(serializers.Field):
    """レスポンス用（読み取り専用）。画像キーを表示用URLにして返す"""

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return image_url(value)
