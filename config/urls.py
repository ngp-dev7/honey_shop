from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from pages.views import root_redirect

urlpatterns = [
    path("", root_redirect, name="root"),
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("pages.urls")),
    prefix_default_language=True,
)
