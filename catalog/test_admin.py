from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .models import Product, Variant
from .test_product_images import MediaTestCase, make_upload, stored_files
from .tests import make_product


def formset_management(prefix, total=0):
    return {
        f"{prefix}-TOTAL_FORMS": total,
        f"{prefix}-INITIAL_FORMS": 0,
        f"{prefix}-MIN_NUM_FORMS": 0,
        f"{prefix}-MAX_NUM_FORMS": 1000,
    }


def product_form_data(category, image=None):
    data = {
        "category": category.pk,
        "slug": "jujube-honey",
        "name_fa": "عسل عناب",
        "name_en": "Jujube honey",
        "summary_fa": "",
        "summary_en": "",
        "description_fa": "",
        "description_en": "",
        "sort_order": 0,
        "is_active": "on",
        **formset_management("variants", total=1),
        "variants-0-sku": "JUJ-500",
        "variants-0-weight_grams": 500,
        "variants-0-label_fa": "",
        "variants-0-label_en": "",
        "variants-0-price_rial": 1_200_000,
        "variants-0-old_price_rial": "",
        "variants-0-stock": 10,
        "variants-0-sort_order": 0,
        "variants-0-is_active": "on",
        **formset_management("specs"),
    }
    if image is None:
        data.update(formset_management("images"))
    else:
        data.update(
            {
                **formset_management("images", total=1),
                "images-0-image": image,
                "images-0-alt_fa": "",
                "images-0-alt_en": "",
                "images-0-sort_order": 0,
            }
        )
    return data


class CatalogAdminTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        admin_user = get_user_model().objects.create_superuser(
            phone="09120000001", password="a-long-test-password-123"
        )
        self.client.force_login(admin_user)
        self.product = make_product()

    def test_admin_pages_load(self):
        urls = [
            reverse("admin:catalog_category_changelist"),
            reverse("admin:catalog_category_add"),
            reverse("admin:catalog_product_changelist"),
            reverse("admin:catalog_product_add"),
            reverse("admin:catalog_product_change", args=[self.product.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_product_list_warns_about_out_of_stock_variants(self):
        Variant.objects.create(
            product=self.product, sku="X-1", weight_grams=500, price_rial=1000, stock=0
        )
        response = self.client.get("/en/admin/catalog/product/")
        self.assertContains(response, "1 variant out of stock")

    def test_add_product_with_variant_and_image(self):
        data = product_form_data(self.product.category, image=make_upload())
        response = self.client.post(reverse("admin:catalog_product_add"), data)
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(slug="jujube-honey")
        self.assertEqual(product.variants.get().sku, "JUJ-500")
        image = product.images.get()
        self.assertTrue(image.files)
        self.assertEqual(len(stored_files()), len(image.files))

    def test_bad_image_is_rejected_and_nothing_is_saved(self):
        bad = SimpleUploadedFile("x.jpg", b"this is not an image")
        data = product_form_data(self.product.category, image=bad)
        response = self.client.post(reverse("admin:catalog_product_add"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(slug="jujube-honey").exists())
        self.assertEqual(stored_files(), [])

    def test_deactivate_and_activate_actions(self):
        url = reverse("admin:catalog_product_changelist")
        post = {"action": "make_inactive", "_selected_action": [self.product.pk]}
        self.client.post(url, post)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        post["action"] = "make_active"
        self.client.post(url, post)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)


class VariantInlineTests(MediaTestCase):
    def setUp(self):
        super().setUp()
        admin_user = get_user_model().objects.create_superuser(
            phone="09120000002", password="a-long-test-password-123"
        )
        self.client.force_login(admin_user)
        self.product = make_product()
        Variant.objects.create(
            product=self.product,
            sku="X-500",
            weight_grams=500,
            price_rial=12_000_000,
            stock=3,
        )

    def change_page(self, language):
        url = f"/{language}/admin/catalog/product/{self.product.pk}/change/"
        return self.client.get(url)

    def test_price_is_shown_in_toman(self):
        self.assertContains(self.change_page("en"), "1,200,000 Toman")
        self.assertContains(self.change_page("fa"), "۱,۲۰۰,۰۰۰ تومان")

    def test_inline_has_the_short_column_set(self):
        response = self.change_page("en")
        self.assertContains(response, "variants-0-price_rial")
        self.assertNotContains(response, "variants-0-label_fa")
        self.assertNotContains(response, "variants-0-sort_order")

    def test_admin_rejects_a_price_that_is_not_whole_toman(self):
        data = product_form_data(self.product.category)
        data["variants-0-price_rial"] = 1_234_567
        response = self.client.post(reverse("admin:catalog_product_add"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(slug="jujube-honey").exists())
