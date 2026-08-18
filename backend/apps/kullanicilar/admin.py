from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.kullanicilar.models import Kullanici


@admin.register(Kullanici)
class KullaniciAdmin(UserAdmin):
    list_display = ("username", "email", "rol", "is_staff", "is_active")
    list_filter = ("rol", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)
    fieldsets = UserAdmin.fieldsets + (("Ürün rolü", {"fields": ("rol",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Ürün rolü", {"fields": ("rol",)}),)
