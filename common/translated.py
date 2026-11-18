from django.conf import settings
from django.utils.translation import get_language


def _language_order():
    """Active language first, then the default one, then the others."""
    codes = [code for code, _name in settings.LANGUAGES]
    active = (get_language() or settings.LANGUAGE_CODE).split("-")[0]
    order = []
    for code in (active, settings.LANGUAGE_CODE, *codes):
        if code in codes and code not in order:
            order.append(code)
    return order


def translated(name):
    """Return a property that reads <name>_<language> from the model.

    Uses the active language when it has a text, and otherwise falls back to
    the default language and then to the others, so a missing translation
    shows another language instead of nothing.
    """

    def getter(self):
        for code in _language_order():
            value = getattr(self, f"{name}_{code}", "")
            if value:
                return value
        return ""

    return property(getter)
