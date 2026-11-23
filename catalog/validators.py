from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from common.formatting import RIAL_PER_TOMAN


def validate_whole_toman(value):
    """Prices are stored in Rial but shown in Toman, so they must be whole Toman."""
    if value % RIAL_PER_TOMAN:
        raise ValidationError(
            _(
                "The price must be a multiple of %(unit)d Rial "
                "(a whole number of Toman)."
            ),
            code="not_whole_toman",
            params={"unit": RIAL_PER_TOMAN},
        )
