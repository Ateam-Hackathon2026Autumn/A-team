"""ファイルの保存とURL

公開画像（商品・農園・体験・プロフィールなど）:
  - save_public_image(user, file): jpg・png だけ（中身を Pillow で読んで判定）、5MB まで。
    写真の向きを反映し、長辺を最大1920pxに縮め、メタデータを除いて圧縮した画像だけ保存する。
    キーは images/{user_id}/{ランダム}.jpg|png。DB には書かない（キーを受け取る側のAPIが保存する）
  - validate_image_keys(user, keys): 受け取ったキーが「images/自分のID/ で始まる」かつ「実在する」かを確かめる

これから追加するもの:
  - 非公開: documents/{user_id}/ランダム（申請書類）、chat/{thread_id}/ランダム（チャット添付）
  - 非公開ファイルは表示のたびに期限付きURL（5分 = settings.PRIVATE_FILE_URL_EXPIRE）

使う場所: POST /uploads/images（実装済み）、生産者の商品登録・更新（実装済み）、農園画像・体験画像・申請・チャット
"""
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import serializers

from .image_compression import compress_uploaded_image


def public_image_prefix(user):
    return f"images/{user.id}/"


def save_public_image(user, uploaded_file):
    """画像を検証・圧縮してから公開用の場所に保存し、キーを返す。"""
    compressed, extension = compress_uploaded_image(uploaded_file)
    key = f"{public_image_prefix(user)}{uuid.uuid4().hex}.{extension}"
    return default_storage.save(key, ContentFile(compressed))


def validate_image_keys(user, keys, field="image_keys"):
    """受け取った画像キーが自分のアップロードしたもので、実在するか。だめなら ValidationError（400）"""
    prefix = public_image_prefix(user)
    for key in keys:
        if not key.startswith(prefix) or ".." in key or not default_storage.exists(key):
            raise serializers.ValidationError({field: ["アップロードした画像を指定してください。"]})
    return keys
