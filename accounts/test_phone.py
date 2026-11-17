from django.test import SimpleTestCase

from .phone import normalize_phone


class NormalizePhoneTests(SimpleTestCase):
    def test_plain_number_is_unchanged(self):
        self.assertEqual(normalize_phone("09123456789"), "09123456789")

    def test_persian_digits(self):
        self.assertEqual(normalize_phone("۰۹۱۲۳۴۵۶۷۸۹"), "09123456789")

    def test_arabic_digits(self):
        self.assertEqual(normalize_phone("٠٩١٢٣٤٥٦٧٨٩"), "09123456789")

    def test_international_formats(self):
        for raw in ("+989123456789", "00989123456789", "989123456789", "9123456789"):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone(raw), "09123456789")

    def test_spaces_and_dashes_are_removed(self):
        self.assertEqual(normalize_phone("+98 (912) 345-6789"), "09123456789")

    def test_invalid_values_return_none(self):
        for raw in (None, "", "abc", "12345", "0212345678", "091234567890"):
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_phone(raw))
