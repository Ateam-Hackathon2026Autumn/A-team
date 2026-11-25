"""アップロード画像の検証・リサイズ・圧縮。"""
import io

from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000  # 縦×横。とても大きい画像でメモリを使い切らないため
MAX_IMAGE_EDGE = 1920
JPEG_QUALITY = 80
FORMATS = {"JPEG": "jpg", "PNG": "png"}


def compress_uploaded_image(uploaded_file) -> tuple[bytes, str]:
    """向きを反映し、メタデータを除いた圧縮済みの画像データと拡張子を返す。"""
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError({"file": ["画像は5MB以下にしてください。"]})
    try:
        with Image.open(uploaded_file) as image, io.BytesIO() as buffer:
            image_format = image.format
            if image_format not in FORMATS or image.width * image.height > MAX_IMAGE_PIXELS:
                raise serializers.ValidationError({"file": ["jpg または png の画像を選んでください。"]})

            ImageOps.exif_transpose(image, in_place=True)
            # 色で透明を指定したPNGは、縮小前に透明度をアルファチャンネルに移す。
            if image_format == "PNG" and max(image.size) > MAX_IMAGE_EDGE and "transparency" in image.info:
                image = image.convert("RGBA")
            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)

            if image_format == "JPEG":
                image.convert("RGB").save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            else:
                transparency = image.info.get("transparency")
                image.info.clear()
                image.save(buffer, format="PNG", optimize=True, transparency=transparency)

            return buffer.getvalue(), FORMATS[image_format]
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise serializers.ValidationError({"file": ["jpg または png の画像を選んでください。"]})
