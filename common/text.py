import re

from .formatting import to_persian_digits

# Arabic letters that look like Persian ones but are different characters.
_ARABIC_TO_PERSIAN = {
    0x064A: "\u06cc",  # Arabic yeh -> Persian yeh
    0x0649: "\u06cc",  # alef maksura -> Persian yeh
    0x0643: "\u06a9",  # Arabic kaf -> Persian kaf
}
# Short vowel marks (U+064B..U+0652) and the stretching line (tatweel, U+0640).
_MARKS = re.compile("[\u064b-\u0652\u0640]")

_ASCII_DIGITS = {}
for _start in (0x06F0, 0x0660):  # Persian and Arabic-Indic digits
    for _i in range(10):
        _ASCII_DIGITS[_start + _i] = str(_i)


def to_ascii_digits(value):
    """Replace Persian and Arabic-Indic digits with ASCII digits."""
    return str(value).translate(_ASCII_DIGITS)


def normalize_persian(value):
    """Make Arabic-keyboard text comparable with Persian text."""
    return _MARKS.sub("", str(value).translate(_ARABIC_TO_PERSIAN))


def digit_forms(word):
    """Return the word with ASCII digits and with Persian digits."""
    ascii_form = to_ascii_digits(word)
    return {ascii_form, to_persian_digits(ascii_form)}
