from django.test import TestCase

from .models import Category, Product, Variant

# Typing "کوهی" on an Arabic keyboard gives different characters.
ARABIC_STYLE = {0x06A9: "\u0643", 0x06CC: "\u064a"}


def make(slug, name_fa="چیز", name_en="", category=None, **extra):
    if category is None:
        category, created = Category.objects.get_or_create(
            slug="honey", defaults={"name_fa": "عسل", "name_en": "Honey"}
        )
    return Product.objects.create(
        category=category, slug=slug, name_fa=name_fa, name_en=name_en, **extra
    )


def add_variant(product, sku, price, **extra):
    return Variant.objects.create(
        product=product, sku=sku, weight_grams=500, price_rial=price, **extra
    )


def slugs(queryset):
    return set(queryset.values_list("slug", flat=True))


class VisibilityTests(TestCase):
    def test_inactive_product_is_hidden(self):
        make("shown")
        make("hidden", is_active=False)
        self.assertEqual(slugs(Product.objects.visible()), {"shown"})

    def test_product_in_inactive_category_is_hidden(self):
        old = Category.objects.create(slug="old", name_fa="قدیمی", is_active=False)
        make("in-old", category=old)
        make("normal")
        self.assertEqual(slugs(Product.objects.visible()), {"normal"})

    def test_visible_categories_need_an_active_product(self):
        shown = Category.objects.create(slug="shown", name_fa="الف")
        only_inactive = Category.objects.create(slug="only-inactive", name_fa="ب")
        Category.objects.create(slug="empty", name_fa="پ")
        inactive_cat = Category.objects.create(
            slug="inactive-cat", name_fa="ت", is_active=False
        )
        make("p1", category=shown)
        make("p2", category=only_inactive, is_active=False)
        make("p3", category=inactive_cat)
        self.assertEqual(slugs(Category.objects.visible()), {"shown"})


class SearchTests(TestCase):
    def test_finds_by_persian_name(self):
        make("a", name_fa="عسل آویشن")
        make("b", name_fa="عسل عناب")
        self.assertEqual(slugs(Product.objects.search("آویشن")), {"a"})

    def test_finds_by_english_name_ignoring_case(self):
        make("a", name_en="Thyme Honey")
        for query in ("thyme", "THYME", "Thyme"):
            with self.subTest(query=query):
                self.assertEqual(slugs(Product.objects.search(query)), {"a"})

    def test_arabic_letters_find_persian_names(self):
        make("a", name_fa="عسل کوهی")
        query = "کوهی".translate(ARABIC_STYLE)
        self.assertNotEqual(query, "کوهی")
        self.assertEqual(slugs(Product.objects.search(query)), {"a"})

    def test_persian_and_ascii_digits_find_each_other(self):
        make("persian", name_fa="عسل ۵۰۰ گرمی")
        make("ascii", name_en="Honey 500 g")
        make("other", name_en="Honey 250 g")
        for query in ("500", "۵۰۰"):
            with self.subTest(query=query):
                self.assertEqual(
                    slugs(Product.objects.search(query)), {"persian", "ascii"}
                )

    def test_all_words_must_match_in_any_order(self):
        make("a", name_en="Thyme honey")
        self.assertEqual(slugs(Product.objects.search("thyme honey")), {"a"})
        self.assertEqual(slugs(Product.objects.search("honey thyme")), {"a"})
        self.assertEqual(slugs(Product.objects.search("thyme jujube")), set())

    def test_finds_by_category_name(self):
        mountain = Category.objects.create(
            slug="mountain", name_fa="کوهستان", name_en="Mountain"
        )
        make("a", name_fa="چیز", category=mountain)
        self.assertEqual(slugs(Product.objects.search("mountain")), {"a"})

    def test_empty_query_returns_everything(self):
        make("a")
        make("b")
        for query in ("", "   ", None):
            with self.subTest(query=query):
                self.assertEqual(slugs(Product.objects.search(query)), {"a", "b"})

    def test_very_long_query_is_safe(self):
        make("a")
        self.assertEqual(Product.objects.search("x" * 5000).count(), 0)

    def test_percent_sign_is_not_a_wildcard(self):
        make("a", name_en="Honey")
        self.assertEqual(slugs(Product.objects.search("%")), set())


class ProductHelperTests(TestCase):
    def test_from_variant_is_the_cheapest_active_one(self):
        product = make("a")
        add_variant(product, "A", 3000)
        add_variant(product, "B", 2000, is_active=False)
        add_variant(product, "C", 2500)
        product = Product.objects.get(pk=product.pk)
        self.assertEqual(product.from_variant.sku, "C")

    def test_product_without_variants(self):
        product = make("a")
        self.assertIsNone(product.from_variant)
        self.assertFalse(product.is_available)

    def test_is_available_needs_an_active_variant_in_stock(self):
        product = make("a")
        add_variant(product, "A", 1000, stock=0)
        add_variant(product, "B", 1000, stock=5, is_active=False)
        self.assertFalse(Product.objects.get(pk=product.pk).is_available)
        add_variant(product, "C", 1000, stock=1)
        self.assertTrue(Product.objects.get(pk=product.pk).is_available)

    def test_discount_percent_is_rounded_down(self):
        product = make("a")
        discounted = add_variant(product, "A", 1000, old_price_rial=1500)
        plain = add_variant(product, "B", 1000)
        self.assertEqual(discounted.discount_percent, 33)
        self.assertEqual(plain.discount_percent, 0)

    def test_main_image_is_none_without_images(self):
        self.assertIsNone(make("a").main_image)


class SearchSafetyTests(TestCase):
    def test_nul_characters_are_ignored(self):
        make("a", name_en="Honey")
        self.assertEqual(slugs(Product.objects.search("ho\x00ney")), {"a"})
