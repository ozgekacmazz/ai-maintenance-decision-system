from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tahminler import services
from apps.tahminler.api.serializers import RiskTahminiGirdiSerializer


class AktifTahminKullanicisiMi(BasePermission):
    message = "Aktif bir USER veya ADMIN hesabı gereklidir."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.rol in {user.Rol.USER, user.Rol.ADMIN}
        )


class RiskTahmini(APIView):
    permission_classes = (IsAuthenticated, AktifTahminKullanicisiMi)

    def post(self, request):
        serializer = RiskTahminiGirdiSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(services.hiyerarsik_risk_tahmini_yap(serializer.validated_data))
