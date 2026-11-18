from django.test import SimpleTestCase
from django.utils import translation

from .translated import translated


class Item:
    title = translated("title")

    def __init__(self, fa="", en=""):
        self.title_fa = fa
        self.title_en = en


class TranslatedTests(SimpleTestCase):
    def test_uses_the_active_language(self):
        item = Item(fa="عسل", en="Honey")
        with translation.override("en"):
            self.assertEqual(item.title, "Honey")
        with translation.override("fa"):
            self.assertEqual(item.title, "عسل")

    def test_empty_english_falls_back_to_persian(self):
        item = Item(fa="عسل")
        with translation.override("en"):
            self.assertEqual(item.title, "عسل")

    def test_empty_persian_falls_back_to_english(self):
        item = Item(en="Honey")
        with translation.override("fa"):
            self.assertEqual(item.title, "Honey")

    def test_both_empty_gives_empty_text(self):
        with translation.override("en"):
            self.assertEqual(Item().title, "")
