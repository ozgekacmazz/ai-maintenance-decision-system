from django.contrib import admin

from apps.bakim.models import (
    ArizaParcaKurali,
    BakimIsEmri,
    IsEmriOlayi,
    Makine,
    Parca,
    Stok,
)


@admin.register(Makine)
class MakineAdmin(admin.ModelAdmin):
    list_display = ("makine_kodu", "ad", "tip", "kritiklik", "aktif")
    list_filter = ("aktif", "kritiklik", "tip")
    search_fields = ("makine_kodu", "ad", "tip")
    ordering = ("makine_kodu",)


@admin.register(Parca)
class ParcaAdmin(admin.ModelAdmin):
    list_display = ("parca_kodu", "ad", "aktif")
    list_filter = ("aktif",)
    search_fields = ("parca_kodu", "ad")
    ordering = ("parca_kodu",)


@admin.register(Stok)
class StokAdmin(admin.ModelAdmin):
    list_display = ("parca", "adet", "minimum_stok", "tedarik_gun")
    search_fields = ("parca__parca_kodu", "parca__ad")
    autocomplete_fields = ("parca",)
    list_select_related = ("parca",)


@admin.register(ArizaParcaKurali)
class ArizaParcaKuraliAdmin(admin.ModelAdmin):
    list_display = ("ariza_tipi", "parca", "aktif")
    list_filter = ("ariza_tipi", "aktif")
    search_fields = ("onerilen_aksiyon", "parca__parca_kodu", "parca__ad")
    autocomplete_fields = ("parca",)
    list_select_related = ("parca",)


class IsEmriOlayInline(admin.TabularInline):
    model = IsEmriOlayi
    extra = 0
    can_delete = False
    readonly_fields = tuple(field.name for field in IsEmriOlayi._meta.fields)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BakimIsEmri)
class BakimIsEmriAdmin(admin.ModelAdmin):
    list_display = (
        "is_emri_numarasi",
        "makine",
        "durum",
        "etkin_oncelik_seviyesi",
        "manuel_oncelik_override",
    )
    list_filter = ("durum", "etkin_oncelik_seviyesi", "manuel_oncelik_override")
    search_fields = ("is_emri_numarasi", "makine__makine_kodu")
    readonly_fields = tuple(field.name for field in BakimIsEmri._meta.fields)
    inlines = (IsEmriOlayInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
