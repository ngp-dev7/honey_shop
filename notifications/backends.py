from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


class SmsBackend:
    """Base class. A real provider implements send_otp()."""

    def send_otp(self, phone, code):
        raise NotImplementedError


class ConsoleSmsBackend(SmsBackend):
    """Development only: prints the code in the terminal."""

    def send_otp(self, phone, code):
        print(f"[SMS] verification code for {phone}: {code}")


class MemorySmsBackend(SmsBackend):
    """For tests: keeps sent messages in a list instead of sending them."""

    outbox = []

    def send_otp(self, phone, code):
        self.outbox.append({"phone": phone, "code": code})


def get_sms_backend():
    backend_class = import_string(settings.SMS_BACKEND)
    if issubclass(backend_class, ConsoleSmsBackend) and not settings.DEBUG:
        raise ImproperlyConfigured(
            "ConsoleSmsBackend must not be used when DEBUG is off."
        )
    return backend_class()
