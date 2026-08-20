from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.bakim.policies import aktif_bakim_kullanicisi_mi, bakim_kaydi_yazabilir_mi


class BakimApiIzni(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return aktif_bakim_kullanicisi_mi(request.user)
        return bakim_kaydi_yazabilir_mi(request.user)
