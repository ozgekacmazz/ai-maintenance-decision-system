from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.kullanicilar.admin import KullaniciAdmin
from apps.kullanicilar.models import Kullanici


def test_custom_user_admin_guvenli_django_yapisini_genisletir():
    model_admin = admin.site._registry[Kullanici]
    assert isinstance(model_admin, KullaniciAdmin)
    assert isinstance(model_admin, UserAdmin)
    assert "rol" in model_admin.list_filter
    assert "is_superuser" in model_admin.list_display
    assert any("rol" in bolum[1]["fields"] for bolum in model_admin.fieldsets)
    assert any("rol" in bolum[1]["fields"] for bolum in model_admin.add_fieldsets)
