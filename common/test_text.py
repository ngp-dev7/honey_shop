from django.test import SimpleTestCase

from .text import digit_forms, normalize_persian, to_ascii_digits


class NormalizePersianTests(SimpleTestCase):
    def test_arabic_letters_become_persian_letters(self):
        arabic = "\u0643\u0648\u0647\u064a"
        self.assertEqual(normalize_persian(arabic), "\u06a9\u0648\u0647\u06cc")

    def test_alef_maksura_becomes_persian_yeh(self):
        self.assertEqual(normalize_persian("\u0649"), "\u06cc")

    def test_vowel_marks_and_tatweel_are_removed(self):
        self.assertEqual(normalize_persian("\u0639\u064e\u0633\u064e\u0644"), "\u0639\u0633\u0644")
        self.assertEqual(normalize_persian("\u0639\u0640\u0633"), "\u0639\u0633")

    def test_persian_text_is_unchanged(self):
        self.assertEqual(normalize_persian("عسل کوهی"), "عسل کوهی")


class DigitTests(SimpleTestCase):
    def test_all_digit_styles_become_ascii(self):
        persian = "".join(chr(0x06F0 + i) for i in range(10))
        arabic = "".join(chr(0x0660 + i) for i in range(10))
        self.assertEqual(to_ascii_digits(persian), "0123456789")
        self.assertEqual(to_ascii_digits(arabic), "0123456789")

    def test_digit_forms(self):
        self.assertEqual(digit_forms("500"), {"500", "۵۰۰"})
        self.assertEqual(digit_forms("۵۰۰"), {"500", "۵۰۰"})
        self.assertEqual(digit_forms("500g"), {"500g", "۵۰۰g"})
        self.assertEqual(digit_forms("honey"), {"honey"})
