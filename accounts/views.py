import logging

from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from . import services
from .forms import CodeForm, PhoneForm

logger = logging.getLogger(__name__)

SESSION_PHONE = "otp_phone"
SESSION_NEXT = "otp_next"


def _safe_next(request, url):
    """Return url only if it points to this site, otherwise an empty string."""
    if url and url_has_allowed_host_and_scheme(
        url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return url
    return ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    next_url = _safe_next(
        request, request.POST.get("next") or request.GET.get("next", "")
    )
    form = PhoneForm(request.POST) if request.method == "POST" else PhoneForm()

    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        ok = True
        try:
            services.request_code(phone, ip=request.META.get("REMOTE_ADDR") or None)
        except services.CooldownActive:
            pass  # A code was sent a moment ago; let the visitor enter it.
        except services.RateLimited:
            ok = False
            form.add_error(None, _("Too many requests. Please try again later."))
        except Exception:
            ok = False
            logger.exception("Could not send the verification SMS")
            form.add_error(
                None,
                _("We could not send the SMS. Please try again in a few minutes."),
            )
        if ok:
            request.session[SESSION_PHONE] = phone
            request.session[SESSION_NEXT] = next_url
            return redirect("accounts:verify")

    return render(request, "accounts/login.html", {"form": form, "next": next_url})


def verify_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    phone = request.session.get(SESSION_PHONE)
    if not phone:
        return redirect("accounts:login")

    form = CodeForm(request.POST) if request.method == "POST" else CodeForm()

    if request.method == "POST" and form.is_valid():
        try:
            user = services.verify_code(phone, form.cleaned_data["code"])
        except services.InvalidCode:
            form.add_error("code", _("The code is wrong or has expired."))
        else:
            next_url = _safe_next(request, request.session.get(SESSION_NEXT, ""))
            login(request, user)
            request.session.pop(SESSION_PHONE, None)
            request.session.pop(SESSION_NEXT, None)
            return redirect(next_url or settings.LOGIN_REDIRECT_URL)

    return render(request, "accounts/verify.html", {"form": form, "phone": phone})
