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
