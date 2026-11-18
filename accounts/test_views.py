from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from notifications.backends import MemorySmsBackend

PHONE = "09123456789"
LOGIN = "/fa/accounts/login/"
VERIFY = "/fa/accounts/verify/"


@override_settings(SMS_BACKEND="notifications.backends.MemorySmsBackend")
class LoginFlowTests(TestCase):
    def setUp(self):
        MemorySmsBackend.outbox.clear()

    def last_code(self):
        return MemorySmsBackend.outbox[-1]["code"]

    def request_code(self):
        return self.client.post(LOGIN, {"phone": PHONE})

    def is_logged_in(self):
        return "_auth_user_id" in self.client.session

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(LOGIN).status_code, 200)

    def test_full_login_flow(self):
        response = self.client.post(LOGIN, {"phone": "۰۹۱۲۳۴۵۶۷۸۹"})
        self.assertRedirects(response, VERIFY, fetch_redirect_response=False)
        response = self.client.post(VERIFY, {"code": self.last_code()})
        self.assertRedirects(response, "/fa/", fetch_redirect_response=False)
        user = get_user_model().objects.get(phone=PHONE)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_english_flow_stays_in_english(self):
        response = self.client.post("/en/accounts/login/", {"phone": PHONE})
        self.assertRedirects(
            response, "/en/accounts/verify/", fetch_redirect_response=False
        )

    def test_invalid_phone_shows_error_and_sends_nothing(self):
        response = self.client.post(LOGIN, {"phone": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("phone", response.context["form"].errors)
        self.assertEqual(MemorySmsBackend.outbox, [])

    def test_verify_without_phone_redirects_to_login(self):
        response = self.client.get(VERIFY)
        self.assertRedirects(response, LOGIN, fetch_redirect_response=False)

    def test_wrong_code_does_not_log_in(self):
        self.request_code()
        wrong = "000000" if self.last_code() != "000000" else "111111"
        response = self.client.post(VERIFY, {"code": wrong})
        self.assertEqual(response.status_code, 200)
        self.assertIn("code", response.context["form"].errors)
        self.assertFalse(self.is_logged_in())

    def test_second_request_within_cooldown_still_reaches_verify(self):
        self.request_code()
        response = self.request_code()
        self.assertRedirects(response, VERIFY, fetch_redirect_response=False)
        self.assertEqual(len(MemorySmsBackend.outbox), 1)

    def test_sms_failure_shows_error(self):
        with override_settings(SMS_BACKEND="accounts.test_services.FailingSmsBackend"):
            with self.assertLogs("accounts.views", level="ERROR"):
                response = self.client.post(LOGIN, {"phone": PHONE})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_safe_next_is_used_after_login(self):
        self.client.post(LOGIN, {"phone": PHONE, "next": "/fa/admin/"})
        response = self.client.post(VERIFY, {"code": self.last_code()})
        self.assertRedirects(response, "/fa/admin/", fetch_redirect_response=False)

    def test_unsafe_next_is_ignored(self):
        for i, bad in enumerate(("https://evil.example/", "//evil.example/")):
            with self.subTest(next=bad):
                self.client = self.client_class()
                phone = f"0912000000{i}"
                self.client.post(LOGIN, {"phone": phone, "next": bad})
                response = self.client.post(VERIFY, {"code": self.last_code()})
                self.assertRedirects(response, "/fa/", fetch_redirect_response=False)

    def test_logged_in_visitor_skips_login(self):
        self.request_code()
        self.client.post(VERIFY, {"code": self.last_code()})
        response = self.client.get(LOGIN)
        self.assertRedirects(response, "/fa/", fetch_redirect_response=False)


class LogoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone=PHONE)
        self.client.force_login(self.user)

    def test_logout_requires_post(self):
        response = self.client.get("/fa/accounts/logout/")
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_logs_out_and_goes_home(self):
        response = self.client.post("/fa/accounts/logout/")
        self.assertRedirects(response, "/fa/", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_english_logout_goes_to_english_home(self):
        response = self.client.post("/en/accounts/logout/")
        self.assertRedirects(response, "/en/", fetch_redirect_response=False)


class HeaderAuthLinksTests(TestCase):
    def test_anonymous_header_has_login_link_with_next(self):
        response = self.client.get("/fa/")
        self.assertContains(response, 'href="/fa/accounts/login/?next=/fa/"')
        self.assertNotContains(response, "/accounts/logout/")

    def test_logged_in_header_has_logout_form_only(self):
        user = get_user_model().objects.create_user(phone=PHONE)
        self.client.force_login(user)
        response = self.client.get("/fa/")
        self.assertContains(response, 'action="/fa/accounts/logout/"')
        self.assertNotContains(response, "/accounts/login/")

    def test_login_page_header_has_no_login_link(self):
        response = self.client.get("/fa/accounts/login/")
        self.assertNotContains(response, 'href="/fa/accounts/login/')
