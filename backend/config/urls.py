from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core.api.schema_views import ProjeDocsView, ProjeSchemaView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.api.urls")),
    path("api/auth/", include("apps.kullanicilar.api.urls")),
    path("api/", include("apps.bakim.api.urls")),
    path("api/tahminler/", include("apps.tahminler.api.urls")),
]

if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path("api/schema/", ProjeSchemaView.as_view(), name="api-schema"),
        path(
            "api/docs/",
            ProjeDocsView.as_view(url_name="api-schema"),
            name="api-docs",
        ),
    ]
