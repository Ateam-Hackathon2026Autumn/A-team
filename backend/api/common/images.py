"""画像キーを表示用URLにする

DB に保存した S3 のキー（ImageField の値、またはサブクエリで取ったキーの文字列）を、表示用のURLに変える。
- キーが空なら None
- 公開画像は署名なしURL（settings.AWS_QUERYSTRING_AUTH = False）。開発・テストでは /media/... になる
- 将来 CDN（CloudFront）のドメインに変えるときは、ここだけ直す

使い方（シリアライザー）:
    url = ImageUrlField(source="image")                  # ImageField
    thumbnail_url = ImageUrlField(source="thumbnail_key")  # サブクエリで取ったキーの文字列
"""
from django.core.files.storage import default_storage
from rest_framework import serializers


def image_url(value):
    """ImageField の値かキーの文字列を受け取り、表示用URLを返す（空なら None）"""
    if not value:
        return None
    key = getattr(value, "name", value)
    if not key:
        return None
    return default_storage.url(key)


class ImageUrlField(serializers.Field):
    """レスポンス用（読み取り専用）。画像キーを表示用URLにして返す"""

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return image_url(value)
