from django.test import TestCase


class HomePageTests(TestCase):
    def test_persian_page_is_rtl(self):
        response = self.client.get("/fa/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="fa"')
        self.assertContains(response, 'dir="rtl"')

    def test_english_page_is_ltr(self):
        response = self.client.get("/en/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, 'dir="ltr"')


class SiteChromeTests(TestCase):
    def test_persian_page_offers_english(self):
        response = self.client.get("/fa/")
        self.assertContains(response, 'name="language" value="en"')
        self.assertNotContains(response, 'name="language" value="fa"')

    def test_english_page_offers_persian(self):
        response = self.client.get("/en/")
        self.assertContains(response, 'name="language" value="fa"')
        self.assertNotContains(response, 'name="language" value="en"')

    def test_language_switch_keeps_the_same_page(self):
        response = self.client.post(
            "/i18n/setlang/", {"language": "en", "next": "/fa/"}
        )
        self.assertRedirects(response, "/en/", fetch_redirect_response=False)

    def test_theme_toggle_and_script_are_present(self):
        response = self.client.get("/fa/")
        self.assertContains(response, "data-theme-toggle")
        self.assertContains(response, "js/theme.js")

    def test_language_buttons_use_their_own_language(self):
        self.assertContains(self.client.get("/fa/"), ">English</button>")
        self.assertContains(self.client.get("/en/"), ">فارسی</button>")
