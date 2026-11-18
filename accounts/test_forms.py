from django.test import SimpleTestCase

from .forms import CodeForm, PhoneForm


class PhoneFormTests(SimpleTestCase):
    def test_persian_digits_are_normalized(self):
        form = PhoneForm({"phone": "۰۹۱۲۳۴۵۶۷۸۹"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["phone"], "09123456789")

    def test_invalid_number_is_rejected(self):
        form = PhoneForm({"phone": "12345"})
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)


class CodeFormTests(SimpleTestCase):
    def test_persian_digits_and_spaces_are_accepted(self):
        form = CodeForm({"code": "۱۲۳ ۴۵۶"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["code"], "123456")

    def test_wrong_codes_are_rejected(self):
        for raw in ("12345", "1234567", "abcdef", ""):
            with self.subTest(raw=raw):
                self.assertFalse(CodeForm({"code": raw}).is_valid())
