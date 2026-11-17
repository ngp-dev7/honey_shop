import io
from contextlib import redirect_stdout

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .backends import MemorySmsBackend, get_sms_backend

MEMORY = "notifications.backends.MemorySmsBackend"
CONSOLE = "notifications.backends.ConsoleSmsBackend"


class SmsBackendTests(SimpleTestCase):
    def setUp(self):
        MemorySmsBackend.outbox.clear()

    @override_settings(SMS_BACKEND=MEMORY)
    def test_memory_backend_keeps_message(self):
        get_sms_backend().send_otp("09123456789", "123456")
        self.assertEqual(
            MemorySmsBackend.outbox,
            [{"phone": "09123456789", "code": "123456"}],
        )

    @override_settings(SMS_BACKEND=CONSOLE, DEBUG=True)
    def test_console_backend_prints_code(self):
        out = io.StringIO()
        with redirect_stdout(out):
            get_sms_backend().send_otp("09123456789", "123456")
        self.assertIn("123456", out.getvalue())
        self.assertIn("09123456789", out.getvalue())

    @override_settings(SMS_BACKEND=CONSOLE, DEBUG=False)
    def test_console_backend_is_refused_when_debug_is_off(self):
        with self.assertRaises(ImproperlyConfigured):
            get_sms_backend()
