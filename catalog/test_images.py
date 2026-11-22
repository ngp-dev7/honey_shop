import io
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from . import images


def make_upload(fmt="PNG", size=(1200, 800), mode="RGB", color=(200, 150, 20)):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format=fmt)
    return SimpleUploadedFile(f"photo.{fmt.lower()}", buffer.getvalue())


def open_result(item):
    return Image.open(io.BytesIO(item.data))


class ValidateImageTests(SimpleTestCase):
    def test_allowed_formats_pass(self):
        for fmt in ("PNG", "JPEG", "WEBP"):
            with self.subTest(fmt=fmt):
                images.validate_image(make_upload(fmt))

    def test_text_file_with_image_name_is_rejected(self):
        upload = SimpleUploadedFile("fake.jpg", b"this is not an image")
        with self.assertRaises(ValidationError) as caught:
            images.validate_image(upload)
        self.assertEqual(caught.exception.code, "invalid_image")

    def test_other_image_formats_are_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            images.validate_image(make_upload("GIF", mode="P", color=0))
        self.assertEqual(caught.exception.code, "invalid_image")

    def test_too_large_file_is_rejected(self):
        upload = SimpleUploadedFile("big.png", b"x" * 200)
        with mock.patch.object(images, "MAX_UPLOAD_BYTES", 100):
            with self.assertRaises(ValidationError) as caught:
                images.validate_image(upload)
        self.assertEqual(caught.exception.code, "too_large")

    def test_too_many_pixels_is_rejected(self):
        with mock.patch.object(images, "MAX_PIXELS", 100):
            with self.assertRaises(ValidationError) as caught:
                images.validate_image(make_upload(size=(20, 20)))
        self.assertEqual(caught.exception.code, "too_many_pixels")

    def test_upload_can_still_be_read_after_validation(self):
        upload = make_upload("PNG")
        images.validate_image(upload)
        self.assertFalse(upload.closed)
        self.assertEqual(len(upload.read()), upload.size)


class ProcessImageTests(SimpleTestCase):
    def test_creates_three_webp_sizes(self):
        result = images.process_image(make_upload(size=(2000, 1000)))
        self.assertEqual(
            [(r.width, r.height) for r in result],
            [(480, 240), (960, 480), (1600, 800)],
        )
        for item in result:
            image = open_result(item)
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (item.width, item.height))

    def test_small_image_is_not_enlarged(self):
        result = images.process_image(make_upload(size=(300, 200)))
        self.assertEqual([(r.width, r.height) for r in result], [(300, 200)])

    def test_phone_rotation_is_applied_and_metadata_removed(self):
        exif = Image.Exif()
        exif[0x0112] = 6  # "rotate 90 degrees"
        buffer = io.BytesIO()
        Image.new("RGB", (1200, 600), (10, 20, 30)).save(
            buffer, format="JPEG", exif=exif
        )
        upload = SimpleUploadedFile("phone.jpg", buffer.getvalue())

        result = images.process_image(upload)

        largest = result[-1]
        self.assertEqual((largest.width, largest.height), (600, 1200))
        self.assertEqual(len(open_result(largest).getexif()), 0)

    def test_transparency_is_kept(self):
        upload = make_upload(mode="RGBA", color=(255, 0, 0, 0), size=(800, 400))
        result = images.process_image(upload)
        self.assertEqual(open_result(result[-1]).mode, "RGBA")

    def test_invalid_upload_raises_validation_error(self):
        upload = SimpleUploadedFile("fake.png", b"not an image")
        with self.assertRaises(ValidationError):
            images.process_image(upload)
