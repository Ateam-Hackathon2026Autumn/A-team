"""画像アップロード のテスト

テスト対象: api/views/public/uploads.py（POST /api/v1/uploads/images）と services/storage.py
保存先はテスト用の一時フォルダー（ApiTestCase）。S3 には接続しない。
"""
import io

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import serializers

from ...services.storage import validate_image_keys
from ..utils import ApiTestCase, make_user

URL = "/api/v1/uploads/images"


def image_file(name="photo.jpg", image_format="JPEG", size=(40, 30), exif=None):
    buffer = io.BytesIO()
    image = Image.new("RGB", size, "green")
    kwargs = {"exif": exif} if exif is not None else {}
    image.save(buffer, format=image_format, **kwargs)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{image_format.lower()}")


def gps_exif():
    exif = Image.Exif()
    exif[0x8825] = {2: (35.0, 41.0, 22.0), 4: (139.0, 41.0, 30.0)}  # GPSInfo（緯度・経度）
    exif[0x0112] = 6  # Orientation（右に90度回転）
    return exif


class ImageUploadTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user(email="farmer@example.com")
        self.signin(self.user.email)

    def test_upload_jpeg_strips_location_and_applies_orientation(self):
        res = self.post_multipart(URL, {"image": image_file(exif=gps_exif())})
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertRegex(body["key"], rf"^images/{self.user.id}/[0-9a-f]{{32}}\.jpg$")
        self.assertEqual(body["url"], f"/media/{body['key']}")
        with default_storage.open(body["key"]) as saved:
            image = Image.open(saved)
            self.assertEqual(image.size, (30, 40))  # 向きを反映して縦長になる
            self.assertEqual(len(image.getexif()), 0)  # 位置情報などは消えている

    def test_upload_png(self):
        res = self.post_multipart(URL, {"image": image_file("logo.png", "PNG")})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["key"].endswith(".png"))

    def test_invalid_files_are_400(self):
        gif = image_file("anim.gif", "GIF")
        fake = SimpleUploadedFile("fake.jpg", b"not an image", content_type="image/jpeg")
        big = SimpleUploadedFile("big.jpg", b"0" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        for data in [{"image": gif}, {"image": fake}, {"image": big}, {}, {"image": image_file(), "foo": "1"}]:
            with self.subTest(data=list(data)):
                res = self.post_multipart(URL, data)
                self.assertEqual((res.status_code, res.json()["errorCode"]), (400, "VALIDATION_ERROR"))

    def test_login_and_csrf_required(self):
        res = self.post_multipart(URL, {"image": image_file()}, csrf=False)
        self.assertEqual((res.status_code, res.json()["errorCode"]), (403, "CSRF_FAILED"))
        self.post_json("/api/v1/auth/signout")
        res = self.post_multipart(URL, {"image": image_file()})
        self.assertEqual(res.status_code, 401)

    def test_validate_image_keys(self):
        mine = self.post_multipart(URL, {"image": image_file()}).json()["key"]
        other = make_user(email="other@example.com")
        self.assertEqual(validate_image_keys(self.user, [mine]), [mine])
        for key in [f"images/{other.id}/x.jpg", f"images/{self.user.id}/missing.jpg",
                    f"images/{self.user.id}/../{other.id}/x.jpg", "documents/1/x.pdf"]:
            with self.subTest(key=key), self.assertRaises(serializers.ValidationError):
                validate_image_keys(self.user, [key])
