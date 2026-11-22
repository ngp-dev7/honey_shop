import io
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import translation
from PIL import Image

from .models import ProductImage, ProductSpec
from .tests import make_product


def make_upload(size=(1200, 800)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 150, 20)).save(buffer, format="PNG")
    return SimpleUploadedFile("photo.png", buffer.getvalue())


def stored_files():
    return [p for p in Path(settings.MEDIA_ROOT).rglob("*") if p.is_file()]


class MediaTestCase(TestCase):
    """Every test gets its own empty media folder."""

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        override = override_settings(MEDIA_ROOT=folder.name)
        override.enable()
        self.addCleanup(override.disable)


class ProductImageTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        self.product = make_product()

    def make_image(self, **kwargs):
        return ProductImage.objects.create(
            product=self.product, image=make_upload(**kwargs)
        )

    def test_upload_is_resized_and_stored_under_random_names(self):
        image = self.make_image(size=(2000, 1000))
        self.assertEqual(sorted(int(w) for w in image.files), [480, 960, 1600])
        for name in image.files.values():
            self.assertTrue(default_storage.exists(name))
            self.assertTrue(name.startswith("products/"))
            self.assertTrue(name.endswith(".webp"))
            self.assertNotIn("photo", name)
        self.assertEqual((image.width, image.height), (1600, 800))
        self.assertEqual(image.image.name, image.files["1600"])

    def test_srcset_lists_all_sizes_smallest_first(self):
        srcset = self.make_image(size=(2000, 1000)).srcset
        widths = [part.split()[-1] for part in srcset.split(", ")]
        self.assertEqual(widths, ["480w", "960w", "1600w"])

    def test_saving_again_keeps_the_files(self):
        image = self.make_image()
        names = list(image.files.values())
        with self.captureOnCommitCallbacks(execute=True):
            image.sort_order = 5
            image.save()
        self.assertEqual(list(image.files.values()), names)
        self.assertTrue(all(default_storage.exists(n) for n in names))

    def test_replacing_the_image_deletes_the_old_files(self):
        image = self.make_image()
        old = list(image.files.values())
        with self.captureOnCommitCallbacks(execute=True):
            image.image = make_upload(size=(900, 600))
            image.save()
        new = list(image.files.values())
        self.assertNotEqual(old, new)
        self.assertFalse(any(default_storage.exists(n) for n in old))
        self.assertTrue(all(default_storage.exists(n) for n in new))

    def test_deleting_the_image_deletes_its_files(self):
        image = self.make_image()
        names = list(image.files.values())
        with self.captureOnCommitCallbacks(execute=True):
            image.delete()
        self.assertFalse(any(default_storage.exists(n) for n in names))

    def test_deleting_the_product_deletes_the_image_files(self):
        image = self.make_image()
        names = list(image.files.values())
        with self.captureOnCommitCallbacks(execute=True):
            self.product.delete()
        self.assertFalse(any(default_storage.exists(n) for n in names))

    def test_invalid_upload_stores_nothing(self):
        bad = SimpleUploadedFile("x.jpg", b"not an image")
        with self.assertRaises(ValidationError):
            ProductImage.objects.create(product=self.product, image=bad)
        self.assertEqual(ProductImage.objects.count(), 0)
        self.assertEqual(stored_files(), [])

    def test_database_failure_removes_the_new_files(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductImage(image=make_upload()).save()  # no product: the insert fails
        self.assertEqual(stored_files(), [])

    def test_description_follows_the_active_language(self):
        image = ProductImage(alt_fa="شیشه عسل", alt_en="Honey jar")
        with translation.override("en"):
            self.assertEqual(image.alt, "Honey jar")
        with translation.override("fa"):
            self.assertEqual(image.alt, "شیشه عسل")


class ProductSpecTests(TestCase):
    def test_label_and_value_follow_the_active_language(self):
        spec = ProductSpec(
            label_fa="منشأ", label_en="Origin", value_fa="ایران", value_en="Iran"
        )
        with translation.override("en"):
            self.assertEqual(str(spec), "Origin: Iran")
        with translation.override("fa"):
            self.assertEqual(str(spec), "منشأ: ایران")

    def test_rows_are_ordered_by_sort_order(self):
        product = make_product()
        ProductSpec.objects.create(
            product=product, label_fa="ب", value_fa="۲", sort_order=2
        )
        ProductSpec.objects.create(
            product=product, label_fa="الف", value_fa="۱", sort_order=1
        )
        self.assertEqual(
            list(product.specs.values_list("sort_order", flat=True)), [1, 2]
        )
