from django.test import TestCase

from catalog.test_queries import add_variant, make


class PersianTranslationTests(TestCase):
    """These fail when the translation is missing or not compiled.

    Fix: python manage.py compilemessages
    """

    def test_home_page_is_translated(self):
        response = self.client.get("/fa/")
        self.assertContains(response, "عسل طبیعی")
        self.assertNotContains(response, "Natural honey")

    def test_english_home_page_stays_english(self):
        self.assertContains(self.client.get("/en/"), "Natural honey")

    def test_product_list_texts_are_translated(self):
        response = self.client.get("/fa/products/")
        self.assertContains(response, "محصولات")
        self.assertContains(response, "جستجوی محصولات")
        self.assertNotContains(response, "Search products")

    def test_login_page_is_translated(self):
        response = self.client.get("/fa/accounts/login/")
        self.assertContains(response, "ارسال کد")
        self.assertNotContains(response, "Send code")

    def test_from_label_is_persian(self):
        product = make("range")
        add_variant(product, "R-1", 10_000, stock=1)
        add_variant(product, "R-2", 20_000, stock=1)
        self.assertContains(
            self.client.get("/fa/products/"), '<span class="muted">از</span>'
        )
