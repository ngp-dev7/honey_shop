import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from notifications.backends import get_sms_backend

from .models import OTPRequest
from .phone import normalize_digits, normalize_phone

OTP_LENGTH = 6
OTP_LIFETIME = timedelta(minutes=2)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_REQUESTS_PER_PHONE_PER_HOUR = 5
MAX_REQUESTS_PER_IP_PER_HOUR = 20


class OTPError(Exception):
    """Base class for all login-code problems."""


class InvalidPhone(OTPError):
    pass


class CooldownActive(OTPError):
    def __init__(self, retry_after):
        super().__init__(f"Try again in {retry_after} seconds.")
        self.retry_after = retry_after


class RateLimited(OTPError):
    pass


class InvalidCode(OTPError):
    pass


def _hash_code(phone, code):
    message = f"{phone}:{code}".encode()
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def request_code(phone_raw, ip=None):
    """Create a one-time code for a phone number and send it by SMS."""
    phone = normalize_phone(phone_raw)
    if phone is None:
        raise InvalidPhone("Invalid mobile number.")

    now = timezone.now()

    last = OTPRequest.objects.filter(phone=phone).first()
    if last and now - last.created_at < RESEND_COOLDOWN:
        remaining = RESEND_COOLDOWN - (now - last.created_at)
        raise CooldownActive(int(remaining.total_seconds()) + 1)

    hour_ago = now - timedelta(hours=1)
    phone_count = OTPRequest.objects.filter(
        phone=phone, created_at__gte=hour_ago
    ).count()
    if phone_count >= MAX_REQUESTS_PER_PHONE_PER_HOUR:
        raise RateLimited("Too many requests for this phone number.")
    if ip:
        ip_count = OTPRequest.objects.filter(
            ip_address=ip, created_at__gte=hour_ago
        ).count()
        if ip_count >= MAX_REQUESTS_PER_IP_PER_HOUR:
            raise RateLimited("Too many requests from this address.")

    code = f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"
    otp = OTPRequest.objects.create(
        phone=phone,
        code_hash=_hash_code(phone, code),
        expires_at=now + OTP_LIFETIME,
        ip_address=ip,
    )
    try:
        get_sms_backend().send_otp(phone, code)
    except Exception:
        # The SMS did not go out, so this must not count against the user.
        otp.delete()
        raise


def verify_code(phone_raw, code_raw):
    """Check a code. Return the user (created if new) or raise InvalidCode."""
    phone = normalize_phone(phone_raw)
    code = "".join(normalize_digits(code_raw or "").split())
    if phone is None:
        raise InvalidCode("Invalid code.")

    now = timezone.now()
    user = None
    with transaction.atomic():
        otp = (
            OTPRequest.objects.select_for_update()
            .filter(
                phone=phone,
                used_at__isnull=True,
                expires_at__gt=now,
                attempts__lt=MAX_ATTEMPTS,
            )
            .order_by("-created_at")
            .first()
        )
        if otp is not None:
            if hmac.compare_digest(otp.code_hash, _hash_code(phone, code)):
                otp.used_at = now
                otp.save(update_fields=["used_at"])
                User = get_user_model()
                candidate = User.objects.filter(phone=phone).first()
                if candidate is None:
                    candidate = User.objects.create_user(phone=phone)
                if candidate.is_active:
                    user = candidate
            else:
                otp.attempts += 1
                otp.save(update_fields=["attempts"])

    # Raised after the transaction, so the attempt counter is really saved.
    if user is None:
        raise InvalidCode("Invalid code.")
    return user
