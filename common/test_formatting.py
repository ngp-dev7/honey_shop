from django.test import SimpleTestCase
from django.utils import translation

from .formatting import format_number, format_price, rial_to_toman, to_persian_digits


class FormattingTests(SimpleTestCase):
    def test_persian_digits(self):
        self.assertEqual(to_persian_digits("0123456789"), "۰۱۲۳۴۵۶۷۸۹")
        self.assertEqual(to_persian_digits(2026), "۲۰۲۶")

    def test_format_number_english(self):
        self.assertEqual(format_number(1200000, "en"), "1,200,000")
        self.assertEqual(format_number(0, "en"), "0")

    def test_format_number_persian(self):
        self.assertEqual(format_number(1200000, "fa"), "۱,۲۰۰,۰۰۰")
        self.assertEqual(format_number(0, "fa"), "۰")

    def test_price_in_toman_english(self):
        self.assertEqual(format_price(12_000_000, "en"), "1,200,000 Toman")

    def test_price_in_toman_persian(self):
        self.assertEqual(format_price(12_000_000, "fa"), "۱,۲۰۰,۰۰۰ تومان")

    def test_uses_the_active_language(self):
        with translation.override("en"):
            self.assertEqual(format_price(10_000), "1,000 Toman")
        with translation.override("fa"):
            self.assertEqual(format_price(10_000), "۱,۰۰۰ تومان")

    def test_rial_to_toman_rounds_down(self):
        self.assertEqual(rial_to_toman(10), 1)
        self.assertEqual(rial_to_toman(19), 1)

    def test_missing_price_gives_empty_text(self):
        self.assertEqual(format_price(None), "")
