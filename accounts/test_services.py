from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from notifications.backends import MemorySmsBackend, SmsBackend

from .models import OTPRequest
from .services import (
    MAX_ATTEMPTS,
    CooldownActive,
    InvalidCode,
    InvalidPhone,
    RateLimited,
    request_code,
    verify_code,
)

PHONE = "09123456789"


class FailingSmsBackend(SmsBackend):
    def send_otp(self, phone, code):
        raise RuntimeError("provider is down")


def other_code(code):
    """Return a six-digit code that is different from the given one."""
    return "000000" if code != "000000" else "111111"


@override_settings(SMS_BACKEND="notifications.backends.MemorySmsBackend")
class OTPServiceTests(TestCase):
    def setUp(self):
        MemorySmsBackend.outbox.clear()

    def last_code(self):
        return MemorySmsBackend.outbox[-1]["code"]

    def age_requests(self, **delta):
        """Make all existing requests look older, e.g. minutes=10."""
        OTPRequest.objects.update(created_at=timezone.now() - timedelta(**delta))

    # --- requesting a code ---

    def test_request_sends_code_to_normalized_phone(self):
        request_code("۰۹۱۲۳۴۵۶۷۸۹")
        self.assertEqual(len(MemorySmsBackend.outbox), 1)
        self.assertEqual(MemorySmsBackend.outbox[0]["phone"], PHONE)
        code = self.last_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_only_a_hash_of_the_code_is_stored(self):
        request_code(PHONE)
        otp = OTPRequest.objects.get()
        self.assertNotEqual(otp.code_hash, self.last_code())
        self.assertEqual(len(otp.code_hash), 64)

    def test_invalid_phone_is_rejected(self):
        with self.assertRaises(InvalidPhone):
            request_code("12345")
        self.assertEqual(MemorySmsBackend.outbox, [])
        self.assertEqual(OTPRequest.objects.count(), 0)

    def test_sms_failure_does_not_keep_request(self):
        with override_settings(SMS_BACKEND="accounts.test_services.FailingSmsBackend"):
            with self.assertRaises(RuntimeError):
                request_code(PHONE)
        self.assertEqual(OTPRequest.objects.count(), 0)

    # --- verifying a code ---

    def test_correct_code_creates_customer(self):
        request_code(PHONE)
        user = verify_code(PHONE, self.last_code())
        self.assertEqual(user.phone, PHONE)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(get_user_model().objects.filter(phone=PHONE).count(), 1)

    def test_code_cannot_be_reused(self):
        request_code(PHONE)
        code = self.last_code()
        verify_code(PHONE, code)
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, code)

    def test_wrong_code_counts_an_attempt(self):
        request_code(PHONE)
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, other_code(self.last_code()))
        self.assertEqual(OTPRequest.objects.get().attempts, 1)

    def test_code_is_locked_after_max_attempts(self):
        request_code(PHONE)
        code = self.last_code()
        for _ in range(MAX_ATTEMPTS):
            with self.assertRaises(InvalidCode):
                verify_code(PHONE, other_code(code))
        self.assertEqual(OTPRequest.objects.get().attempts, MAX_ATTEMPTS)
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, code)
        self.assertFalse(get_user_model().objects.filter(phone=PHONE).exists())

    def test_expired_code_is_rejected(self):
        request_code(PHONE)
        OTPRequest.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, self.last_code())

    def test_persian_digits_in_code_are_accepted(self):
        request_code(PHONE)
        persian = self.last_code().translate(
            {ord(str(i)): chr(0x06F0 + i) for i in range(10)}
        )
        user = verify_code(PHONE, persian)
        self.assertEqual(user.phone, PHONE)

    def test_unknown_phone_gets_same_error(self):
        with self.assertRaises(InvalidCode):
            verify_code("09125555555", "123456")

    def test_inactive_user_cannot_log_in(self):
        get_user_model().objects.create_user(phone=PHONE, is_active=False)
        request_code(PHONE)
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, self.last_code())

    # --- limits ---

    def test_cooldown_blocks_quick_resend(self):
        request_code(PHONE)
        with self.assertRaises(CooldownActive):
            request_code(PHONE)
        self.assertEqual(len(MemorySmsBackend.outbox), 1)

    def test_new_code_replaces_old_code(self):
        request_code(PHONE)
        first = self.last_code()
        self.age_requests(minutes=2)
        request_code(PHONE)
        second = self.last_code()
        if first == second:
            self.skipTest("random codes happened to be equal")
        with self.assertRaises(InvalidCode):
            verify_code(PHONE, first)
        self.assertEqual(verify_code(PHONE, second).phone, PHONE)

    def test_phone_hourly_limit(self):
        for _ in range(5):
            request_code(PHONE)
            self.age_requests(minutes=10)
        with self.assertRaises(RateLimited):
            request_code(PHONE)
        self.assertEqual(len(MemorySmsBackend.outbox), 5)

    def test_ip_hourly_limit(self):
        for i in range(20):
            request_code(f"0912{i:07d}", ip="203.0.113.7")
        with self.assertRaises(RateLimited):
            request_code("09129999999", ip="203.0.113.7")
        self.assertEqual(len(MemorySmsBackend.outbox), 20)
