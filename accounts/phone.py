import re

# Map Persian (U+06F0..) and Arabic-Indic (U+0660..) digits to ASCII digits.
_DIGIT_MAP = {}
for _start in (0x06F0, 0x0660):
    for _i in range(10):
        _DIGIT_MAP[_start + _i] = str(_i)

# Spaces, dashes, brackets, dots, and invisible direction marks.
_SEPARATORS = re.compile(r"[\s\-().\u200c\u200e\u200f]")
_MOBILE = re.compile(r"^09\d{9}$")


def normalize_digits(value):
    """Convert Persian and Arabic-Indic digits to ASCII digits."""
    return str(value).translate(_DIGIT_MAP)


def normalize_phone(raw):
    """Return an Iranian mobile number as 09XXXXXXXXX, or None if invalid."""
    if not raw:
        return None

    value = normalize_digits(raw)
    value = _SEPARATORS.sub("", value)

    if value.startswith("+"):
        value = value[1:]
    if value.startswith("0098"):
        value = value[4:]
    elif value.startswith("98") and len(value) == 12:
        value = value[2:]
    if len(value) == 10 and value.startswith("9"):
        value = "0" + value

    return value if _MOBILE.match(value) else None
