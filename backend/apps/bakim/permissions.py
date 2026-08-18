from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.bakim.policies import bakim_kaydi_yazabilir_mi


class BakimApiIzni(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bakim_kaydi_yazabilir_mi(request.user)
