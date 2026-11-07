"""S3 の元画像を圧縮し、同じバケットの別 prefix に保存する。"""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import logging
import os
import re
from urllib.parse import unquote_plus
import warnings

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from PIL import Image, ImageOps, UnidentifiedImageError


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SkipImage(Exception):
    """再試行しても処理できない入力。理由を記録して終了する。"""


@dataclass(frozen=True)
class Settings:
    bucket: str
    owner: str
    input_prefix: str
    output_prefix: str
    output_format: str
    quality: int
    max_width: int
    max_height: int
    max_input_bytes: int
    max_input_pixels: int
    revision: str

    @classmethod
    def from_environment(cls):
        settings = cls(
            bucket=os.environ["BUCKET_NAME"],
            owner=os.environ["BUCKET_OWNER"],
            input_prefix=os.environ["INPUT_PREFIX"],
            output_prefix=os.environ["OUTPUT_PREFIX"],
            output_format=os.environ["OUTPUT_FORMAT"],
            quality=int(os.environ["QUALITY"]),
            max_width=int(os.environ["MAX_WIDTH"]),
            max_height=int(os.environ["MAX_HEIGHT"]),
            max_input_bytes=int(os.environ["MAX_INPUT_BYTES"]),
            max_input_pixels=int(os.environ["MAX_INPUT_PIXELS"]),
            revision=os.environ["PROCESSOR_REVISION"],
        )
        settings.validate()
        return settings

    def validate(self):
        for prefix in (self.input_prefix, self.output_prefix):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_.-]*/", prefix) or len(prefix) > 512:
                raise ValueError("Invalid S3 prefix")
        if self.output_prefix.startswith(self.input_prefix) or self.input_prefix.startswith(self.output_prefix):
            raise ValueError("Input and output prefixes must not overlap")
        if self.output_format not in ("webp", "jpeg", "png") or not 1 <= self.quality <= 95:
            raise ValueError("Invalid image format or quality")
        if not (1 <= self.max_width <= 8192 and 1 <= self.max_height <= 8192):
            raise ValueError("Invalid image dimensions")
        if not (1 <= self.max_input_bytes <= 100 * 1024 * 1024 and 1 <= self.max_input_pixels <= 40000000):
            raise ValueError("Invalid input size limits")

    def output_key(self, source_key, version, etag):
        # バージョンと圧縮設定ごとにキーを分離し、古い通知が新しい結果を上書きするのを防ぐ。
        identity = json.dumps(
            [version, etag, self.output_format, self.quality, self.max_width, self.max_height, self.revision],
            separators=(",", ":"),
        )
        digest = sha256(identity.encode()).hexdigest()
        extension = "jpg" if self.output_format == "jpeg" else self.output_format
        relative_key = source_key[len(self.input_prefix):]
        key = f"{self.output_prefix}{relative_key}.{digest}.{extension}"
        if len(key.encode("utf-8")) > 1024:
            raise SkipImage("output_key_too_long")
        return key


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client("s3", config=BotoConfig(retries={"mode": "standard", "max_attempts": 3}))


def compress_image(data, settings):
    """縦横比と向きを維持して縮小する。アニメーションは変換しない。"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as source:
                if source.width * source.height > settings.max_input_pixels:
                    raise SkipImage("too_many_pixels")
                if getattr(source, "n_frames", 1) > 1:
                    raise SkipImage("animated_image")
                source.load()
                image = ImageOps.exif_transpose(source)
                image.thumbnail((settings.max_width, settings.max_height), Image.Resampling.LANCZOS)
                # JPEG 出力のみ透過部分を白で埋める。WebP / PNG は透過を維持する。
                if settings.output_format == "jpeg":
                    rgba = image.convert("RGBA")
                    image = Image.new("RGB", rgba.size, "white")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
                # 位置情報を含む EXIF 等の付加情報を出力へ引き継がない。
                image.info.clear()
                output = BytesIO()
                if settings.output_format == "webp":
                    image.save(output, "WEBP", quality=settings.quality, method=4)
                elif settings.output_format == "jpeg":
                    image.save(output, "JPEG", quality=settings.quality, optimize=True, progressive=True)
                else:
                    image.save(output, "PNG", optimize=True, compress_level=9)
                return output.getvalue(), image.width, image.height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise SkipImage("unsupported_or_invalid_image") from error


def process_record(record, settings, s3):
    if record.get("eventSource") != "aws:s3" or not record.get("eventName", "").startswith("ObjectCreated:"):
        return {"status": "skipped", "reason": "not_object_created"}
    source = record["s3"]
    key = unquote_plus(source["object"]["key"])
    if source["bucket"]["name"] != settings.bucket or not key.startswith(settings.input_prefix) or key.startswith(settings.output_prefix):
        return {"status": "skipped", "reason": "outside_input_prefix"}
    if key.endswith("/"):
        return {"status": "skipped", "reason": "folder_marker"}
    if source["object"].get("size", 0) > settings.max_input_bytes:
        return {"status": "skipped", "reason": "input_too_large"}

    try:
        request = {"Bucket": settings.bucket, "Key": key, "ExpectedBucketOwner": settings.owner}
        version = source["object"].get("versionId")
        if version and version != "null":
            request["VersionId"] = version
        else:
            # バージョニングが無効な場合も、通知後に変更された別の内容は取り込まない。
            etag = source["object"].get("eTag")
            if not etag:
                raise SkipImage("missing_object_identity")
            request["IfMatch"] = f'"{etag.strip(chr(34))}"'
        try:
            response = s3.get_object(**request)
        except ClientError as error:
            if error.response["Error"]["Code"] in ("NoSuchKey", "NoSuchVersion", "PreconditionFailed", "404", "412"):
                raise SkipImage("source_deleted_or_replaced") from error
            raise
        stream = response["Body"]
        try:
            if response["ContentLength"] > settings.max_input_bytes:
                raise SkipImage("input_too_large")
            data = stream.read(settings.max_input_bytes + 1)
            if len(data) > settings.max_input_bytes:
                raise SkipImage("input_too_large")
        finally:
            stream.close()
        output_key = settings.output_key(key, response.get("VersionId", ""), response["ETag"])
        compressed, width, height = compress_image(data, settings)
        try:
            s3.put_object(
                Bucket=settings.bucket,
                Key=output_key,
                Body=compressed,
                ContentType=f"image/{settings.output_format}",
                CacheControl="max-age=31536000, immutable",
                ServerSideEncryption="AES256",
                ExpectedBucketOwner=settings.owner,
                IfNoneMatch="*",
                Metadata={
                    "source-key-sha256": sha256(key.encode()).hexdigest(),
                    "source-version": response.get("VersionId", ""),
                    "source-etag": response["ETag"].strip('"'),
                },
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in ("PreconditionFailed", "412"):
                return {"status": "already_exists", "key": key, "output_key": output_key}
            raise
        return {
            "status": "created", "key": key, "output_key": output_key,
            "input_bytes": len(data), "output_bytes": len(compressed), "width": width, "height": height,
        }
    except SkipImage as error:
        return {"status": "skipped", "key": key, "reason": str(error)}


def lambda_handler(event, context):
    if event.get("Event") == "s3:TestEvent":
        return {"status": "test_event"}
    settings = Settings.from_environment()
    results = []
    failures = 0
    for record in event.get("Records", []):
        try:
            result = process_record(record, settings, get_s3_client())
            logger.info(json.dumps(result, ensure_ascii=False))
            results.append(result)
        except Exception:
            failures += 1
            logger.exception("Image compression failed; Lambda will retry the event")
    if failures:
        # 一部が成功していても、条件付き書き込みにより再試行で重複保存されない。
        raise RuntimeError(f"{failures} image record(s) failed")
    return {"results": results}
