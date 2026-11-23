from django import template

from common.formatting import format_number, format_price

register = template.Library()


@register.filter
def price(rial):
    """Show a price stored in Rial as Toman, in the active language."""
    return format_price(rial)


@register.filter
def localnum(value):
    """Show a whole number with the digits of the active language."""
    return format_number(value)
