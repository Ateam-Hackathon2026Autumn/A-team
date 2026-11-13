"""ファイルの保存とURL

公開画像（商品・農園・体験・プロフィールなど）:
  - save_public_image(user, file): jpg・png だけ（中身を Pillow で読んで判定）、5MB まで。
    位置情報などのメタデータ（EXIF）を消すため、読み込んで保存し直す（向きは先に反映する）。
    キーは images/{user_id}/{ランダム}.jpg|png。DB には書かない（キーを受け取る側のAPIが保存する）
  - validate_image_keys(user, keys): 受け取ったキーが「images/自分のID/ で始まる」かつ「実在する」かを確かめる

これから追加するもの:
  - 非公開: documents/{user_id}/ランダム（申請書類）、chat/{thread_id}/ランダム（チャット添付）
  - 非公開ファイルは表示のたびに期限付きURL（5分 = settings.PRIVATE_FILE_URL_EXPIRE）

使う場所: POST /uploads/images（実装済み）、生産者の商品登録・更新（実装済み）、農園画像・体験画像・申請・チャット
"""
import io
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000  # 縦×横。とても大きい画像でメモリを使い切らないため
FORMATS = {"JPEG": "jpg", "PNG": "png"}


def public_image_prefix(user):
    return f"images/{user.id}/"


def save_public_image(user, uploaded_file):
    """画像を検証し、メタデータを消して公開用の場所に保存する。保存したキーを返す。不正なら ValidationError"""
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError({"image": ["画像は5MB以下にしてください。"]})
    try:
        image = Image.open(uploaded_file)
        if image.format not in FORMATS or image.width * image.height > MAX_IMAGE_PIXELS:
            raise serializers.ValidationError({"image": ["jpg または png の画像を選んでください。"]})
        image_format = image.format
        image = ImageOps.exif_transpose(image)  # スマホ写真の向きを反映してから、メタデータを捨てる
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise serializers.ValidationError({"image": ["jpg または png の画像を選んでください。"]})

    buffer = io.BytesIO()
    if image_format == "JPEG":
        image.convert("RGB").save(buffer, format="JPEG", quality=90)
    else:
        image.save(buffer, format="PNG")
    key = f"{public_image_prefix(user)}{uuid.uuid4().hex}.{FORMATS[image_format]}"
    return default_storage.save(key, ContentFile(buffer.getvalue()))


def validate_image_keys(user, keys, field="image_keys"):
    """受け取った画像キーが自分のアップロードしたもので、実在するか。だめなら ValidationError（400）"""
    prefix = public_image_prefix(user)
    for key in keys:
        if not key.startswith(prefix) or ".." in key or not default_storage.exists(key):
            raise serializers.ValidationError({field: ["アップロードした画像を指定してください。"]})
    return keys
