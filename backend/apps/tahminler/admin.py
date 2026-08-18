from django.contrib import admin

from apps.tahminler.models import (
    ArizaTipiSnapshot,
    BakimKarariSnapshot,
    ErpSnapshot,
    KararAksiyonuSnapshot,
    KararGerekcesiSnapshot,
    KararUyarisiSnapshot,
    ReplayOgesi,
    ReplayOlayi,
    ReplayOturumu,
    ShapEtkisiSnapshot,
    TahminKaydi,
)


class SaltOkunurSnapshotAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TahminKaydi)
class TahminKaydiAdmin(SaltOkunurSnapshotAdmin):
    list_display = ("id", "makine_kodu_snapshot", "olcum_zamani", "risk_uyarisi")


admin.site.register(ArizaTipiSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(ShapEtkisiSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(ErpSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(BakimKarariSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(KararGerekcesiSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(KararAksiyonuSnapshot, SaltOkunurSnapshotAdmin)
admin.site.register(KararUyarisiSnapshot, SaltOkunurSnapshotAdmin)


class ReplayOgeInline(admin.TabularInline):
    model = ReplayOgesi
    extra = 0
    can_delete = False
    exclude = ("processing_token", "sensor_snapshot")
    readonly_fields = tuple(
        field.name
        for field in ReplayOgesi._meta.fields
        if field.name not in {"processing_token", "sensor_snapshot"}
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReplayOturumu)
class ReplayOturumuAdmin(SaltOkunurSnapshotAdmin):
    list_display = ("replay_numarasi", "durum", "split", "olusturan", "toplam_oge")
    list_filter = ("durum", "split", "olusturan")
    search_fields = ("replay_numarasi",)
    exclude = ("aktif_claim_token",)
    inlines = (ReplayOgeInline,)


admin.site.register(ReplayOlayi, SaltOkunurSnapshotAdmin)
