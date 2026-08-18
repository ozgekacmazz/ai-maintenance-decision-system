from django.contrib import admin

from apps.tahminler.models import (
    ArizaTipiSnapshot,
    ErpSnapshot,
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
