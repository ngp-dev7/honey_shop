from django import forms
from django.utils.translation import gettext_lazy as _

from .phone import normalize_digits, normalize_phone
from .services import OTP_LENGTH


class PhoneForm(forms.Form):
    phone = forms.CharField(
        label=_("Mobile number"),
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "type": "tel",
                "inputmode": "numeric",
                "autocomplete": "tel",
                "dir": "ltr",
                "autofocus": True,
                "placeholder": "09123456789",
            }
        ),
    )

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if phone is None:
            raise forms.ValidationError(
                _("Enter a valid Iranian mobile number, like 09123456789.")
            )
        return phone


class CodeForm(forms.Form):
    code = forms.CharField(
        label=_("Verification code"),
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "input input--code",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "dir": "ltr",
                "autofocus": True,
            }
        ),
    )

    def clean_code(self):
        code = "".join(normalize_digits(self.cleaned_data["code"]).split())
        if len(code) != OTP_LENGTH or not (code.isascii() and code.isdigit()):
            raise forms.ValidationError(
                _("Enter the %(length)s-digit code.") % {"length": OTP_LENGTH}
            )
        return code
