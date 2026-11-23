from django.conf import settings
from django.utils.translation import get_language

RIAL_PER_TOMAN = 10
CURRENCY_UNITS = {"fa": "تومان", "en": "Toman"}

_PERSIAN_DIGITS = {ord(str(i)): chr(0x06F0 + i) for i in range(10)}


def to_persian_digits(value):
    """Replace ASCII digits with Persian digits."""
    return str(value).translate(_PERSIAN_DIGITS)


def _language(language=None):
    default = settings.LANGUAGE_CODE.split("-")[0]
    code = (language or get_language() or default).split("-")[0]
    return code if code in CURRENCY_UNITS else default


def rial_to_toman(rial):
    return rial // RIAL_PER_TOMAN


def format_number(number, language=None):
    """1200000 -> "1,200,000" (or with Persian digits in Persian)."""
    text = f"{number:,}"
    return to_persian_digits(text) if _language(language) == "fa" else text


def format_price(rial, language=None):
    """Return a price in Rial as Toman text, for example "1,200,000 Toman"."""
    if rial is None:
        return ""
    code = _language(language)
    return f"{format_number(rial_to_toman(rial), code)} {CURRENCY_UNITS[code]}"
