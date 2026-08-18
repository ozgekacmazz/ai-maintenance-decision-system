from django.contrib import admin

from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok


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
