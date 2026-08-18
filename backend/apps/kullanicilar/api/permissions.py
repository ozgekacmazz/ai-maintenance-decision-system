from rest_framework.permissions import BasePermission

from apps.kullanicilar.policies import aktif_admin_mi


class UrunAdminiMi(BasePermission):
    message = "Bu işlem için ADMIN rolü gereklidir."

    def has_permission(self, request, view):
        return aktif_admin_mi(request.user)
