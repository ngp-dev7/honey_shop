from django.conf import settings
from django.test import TestCase


class RootRedirectTests(TestCase):
    def test_new_visitor_goes_to_persian_even_with_english_browser(self):
        response = self.client.get("/", headers={"Accept-Language": "en"})
        self.assertRedirects(response, "/fa/", fetch_redirect_response=False)

    def test_returning_english_visitor_goes_to_english(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.get("/")
        self.assertRedirects(response, "/en/", fetch_redirect_response=False)

    def test_unknown_cookie_value_falls_back_to_persian(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "xx"
        response = self.client.get("/")
        self.assertRedirects(response, "/fa/", fetch_redirect_response=False)
