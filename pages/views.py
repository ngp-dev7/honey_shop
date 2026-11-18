from django.conf import settings
from django.shortcuts import redirect
from django.utils import translation


def root_redirect(request):
    """Send "/" to the visitor's chosen language, Persian by default."""
    language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if language not in dict(settings.LANGUAGES):
        language = settings.LANGUAGE_CODE
    with translation.override(language):
        return redirect("pages:home")
