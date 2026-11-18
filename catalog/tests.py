from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import translation

from .models import Category, Product, Variant


def make_product(slug="thyme-honey"):
    category, created = Category.objects.get_or_create(
        slug="thyme", defaults={"name_fa": "آویشن", "name_en": "Thyme"}
    )
    return Product.objects.create(
        category=category, slug=slug, name_fa="عسل آویشن", name_en="Thyme honey"
    )


def make_variant(product, sku="THY-500", price=1000, old_price=None, **extra):
    return Variant(
        product=product,
        sku=sku,
        weight_grams=500,
        price_rial=price,
        old_price_rial=old_price,
        **extra,
    )


class TranslatedNameTests(TestCase):
    def test_names_follow_the_active_language(self):
        product = make_product()
        with translation.override("en"):
            self.assertEqual(product.name, "Thyme honey")
            self.assertEqual(product.category.name, "Thyme")
        with translation.override("fa"):
            self.assertEqual(product.name, "عسل آویشن")

    def test_missing_english_name_falls_back_to_persian(self):
        category = Category(slug="x", name_fa="چند گیاه")
        with translation.override("en"):
            self.assertEqual(str(category), "چند گیاه")


class VariantPriceTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_valid_discount_passes_validation(self):
        make_variant(self.product, price=1000, old_price=1500).full_clean()

    def test_old_price_must_be_higher_than_price(self):
        for old_price in (1000, 500):
            with self.subTest(old_price=old_price):
                variant = make_variant(self.product, price=1000, old_price=old_price)
                with self.assertRaises(ValidationError):
                    variant.full_clean()

    def test_database_rejects_a_bad_old_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_variant(self.product, price=1000, old_price=900).save()

    def test_price_cannot_be_zero(self):
        with self.assertRaises(ValidationError):
            make_variant(self.product, price=0).full_clean()


class CatalogRulesTests(TestCase):
    def test_sku_must_be_unique(self):
        product = make_product()
        make_variant(product, sku="THY-500").save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_variant(product, sku="THY-500").save()

    def test_category_with_products_cannot_be_deleted(self):
        product = make_product()
        with self.assertRaises(ProtectedError):
            product.category.delete()

    def test_in_stock_follows_stock_count(self):
        product = make_product()
        self.assertFalse(make_variant(product, stock=0).is_in_stock)
        self.assertTrue(make_variant(product, stock=3).is_in_stock)
