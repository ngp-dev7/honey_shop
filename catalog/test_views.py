from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import translation

from .models import Category, ProductImage
from .templatetags.catalog_extras import localnum, price
from .test_product_images import MediaTestCase, make_upload
from .test_queries import ARABIC_STYLE, add_variant, make

EN = "/en/products/"
FA = "/fa/products/"


def slugs_on(response):
    return [product.slug for product in response.context["products"]]


class ProductListTests(TestCase):
    def test_only_visible_products_are_listed(self):
        make("shown", name_en="Shown honey")
        make("hidden", name_en="Hidden honey", is_active=False)
        old = Category.objects.create(slug="old", name_fa="قدیمی", is_active=False)
        make("in-old", name_en="Old honey", category=old)
        response = self.client.get(EN)
        self.assertEqual(slugs_on(response), ["shown"])
        self.assertNotContains(response, "Hidden honey")
        self.assertNotContains(response, "Old honey")

    def test_empty_list_shows_a_message(self):
        self.assertContains(self.client.get(EN), "No products found.")

    def test_names_follow_the_language(self):
        make("a", name_fa="عسل آویشن", name_en="Thyme honey")
        self.assertContains(self.client.get(EN), "Thyme honey")
        self.assertContains(self.client.get(FA), "عسل آویشن")

    def test_price_is_shown_in_toman_for_each_language(self):
        add_variant(make("a"), "A-1", 12_000_000, stock=5)
        self.assertContains(self.client.get(EN), "1,200,000 Toman")
        self.assertContains(self.client.get(FA), "۱,۲۰۰,۰۰۰ تومان")

    def test_discount_badge_and_old_price(self):
        add_variant(make("a"), "A-1", 10_000, old_price_rial=15_000, stock=5)
        response = self.client.get(EN)
        self.assertContains(response, "33%")
        self.assertContains(response, "1,500 Toman")

    def test_out_of_stock_badge(self):
        add_variant(make("empty"), "E-1", 1000, stock=0)
        self.assertContains(self.client.get(EN), "Out of stock")

    def test_available_product_has_no_out_of_stock_badge(self):
        add_variant(make("full"), "F-1", 1000, stock=3)
        self.assertNotContains(self.client.get(EN), "Out of stock")

    def test_names_are_escaped(self):
        make("evil", name_en="<script>alert(1)</script>")
        response = self.client.get(EN)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")


class CategoryPageTests(TestCase):
    def setUp(self):
        self.herbs = Category.objects.create(
            slug="herbs", name_fa="گیاهی", name_en="Herbs"
        )
        self.fruit = Category.objects.create(
            slug="fruit", name_fa="میوه", name_en="Fruit"
        )
        make("thyme", category=self.herbs)
        make("jujube", category=self.fruit)

    def test_category_page_lists_only_its_products(self):
        response = self.client.get(f"{EN}category/herbs/")
        self.assertEqual(slugs_on(response), ["thyme"])

    def test_chips_link_to_visible_categories(self):
        response = self.client.get(EN)
        self.assertContains(response, 'href="/en/products/category/herbs/"')
        self.assertContains(response, 'href="/en/products/category/fruit/"')

    def test_unknown_category_is_not_found(self):
        self.assertEqual(self.client.get(f"{EN}category/nope/").status_code, 404)

    def test_inactive_category_is_not_found(self):
        self.fruit.is_active = False
        self.fruit.save()
        self.assertEqual(self.client.get(f"{EN}category/fruit/").status_code, 404)

    def test_category_without_active_products_is_not_found(self):
        Category.objects.create(slug="empty", name_fa="خالی")
        self.assertEqual(self.client.get(f"{EN}category/empty/").status_code, 404)


class SearchViewTests(TestCase):
    def test_search_finds_matching_products(self):
        make("a", name_en="Thyme honey")
        make("b", name_en="Jujube honey")
        response = self.client.get(EN, {"q": "thyme"})
        self.assertEqual(slugs_on(response), ["a"])

    def test_search_with_arabic_letters_finds_persian_names(self):
        make("a", name_fa="عسل کوهی")
        response = self.client.get(EN, {"q": "کوهی".translate(ARABIC_STYLE)})
        self.assertEqual(slugs_on(response), ["a"])

    def test_no_match_shows_a_message(self):
        make("a", name_en="Thyme honey")
        self.assertContains(self.client.get(EN, {"q": "zzz"}), "No products found.")

    def test_nul_character_does_not_cause_an_error(self):
        make("a", name_en="Honey")
        self.assertEqual(self.client.get(EN + "?q=%00").status_code, 200)

    def test_search_is_kept_in_category_links_and_pagination(self):
        for i in range(13):
            make(f"h{i:02d}", name_en=f"Honey {i}")
        response = self.client.get(EN, {"q": "honey"})
        self.assertContains(response, "q=honey&amp;page=2")
        self.assertContains(response, "category/")  # chips are still there


class PaginationTests(TestCase):
    def setUp(self):
        for i in range(13):
            make(f"p{i:02d}")

    def test_first_page_has_twelve_products(self):
        response = self.client.get(EN)
        self.assertEqual(len(slugs_on(response)), 12)
        self.assertContains(response, "page=2")

    def test_second_page_has_the_rest(self):
        self.assertEqual(slugs_on(self.client.get(EN, {"page": 2})), ["p12"])

    def test_bad_page_numbers_never_cause_an_error(self):
        first = self.client.get(EN, {"page": "abc"})
        last = self.client.get(EN, {"page": 999})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(slugs_on(first)), 12)
        self.assertEqual(last.status_code, 200)
        self.assertEqual(slugs_on(last), ["p12"])

    def test_page_numbers_use_persian_digits_in_persian(self):
        self.assertContains(self.client.get(FA), "۱")


class QueryCountTests(MediaTestCase):
    def add_products(self, start, stop):
        for i in range(start, stop):
            product = make(f"q{i:02d}", name_fa=f"محصول {i}")
            add_variant(product, f"Q-{i}-A", 10_000 * (i + 1), stock=3)
            add_variant(product, f"Q-{i}-B", 20_000 * (i + 1), stock=3)
            ProductImage.objects.create(product=product, image=make_upload((300, 300)))

    def count_queries(self, url):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(queries)

    def test_query_count_does_not_grow_with_the_number_of_products(self):
        self.add_products(0, 3)
        few = self.count_queries(EN)
        self.add_products(3, 12)
        many = self.count_queries(EN)
        self.assertEqual(few, many)


class TemplateFilterTests(SimpleTestCase):
    def test_price_filter(self):
        with translation.override("en"):
            self.assertEqual(price(12_000_000), "1,200,000 Toman")
        with translation.override("fa"):
            self.assertEqual(price(12_000_000), "۱,۲۰۰,۰۰۰ تومان")

    def test_localnum_filter(self):
        with translation.override("en"):
            self.assertEqual(localnum(1234), "1,234")
        with translation.override("fa"):
            self.assertEqual(localnum(1234), "۱,۲۳۴")
