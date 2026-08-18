from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bakim.api.pagination import BakimSayfalama
from apps.tahminler import services
from apps.tahminler.api.serializers import (
    RiskTahminiGirdiSerializer,
    TahminKaydiDetaySerializer,
    TahminKaydiFiltreSerializer,
    TahminKaydiListeSerializer,
    TahminKaydiYazmaSerializer,
)
from apps.tahminler.record_services import tahmin_kaydi_olustur
from apps.tahminler.selectors import tahmin_kaydi_detayi, tahmin_kaydi_listesi


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


class TahminKaydiListesi(APIView):
    permission_classes = (IsAuthenticated, AktifTahminKullanicisiMi)

    def get(self, request):
        filtre = TahminKaydiFiltreSerializer(data=request.query_params)
        filtre.is_valid(raise_exception=True)
        queryset = tahmin_kaydi_listesi(filtreler=filtre.validated_data)
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(queryset, request, self)
        return paginator.get_paginated_response(
            TahminKaydiListeSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = TahminKaydiYazmaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record, repeated = tahmin_kaydi_olustur(
            kullanici=request.user,
            trace_id=request.trace_id,
            veriler=serializer.validated_data,
        )
        record = get_object_or_404(tahmin_kaydi_detayi(), pk=record.pk)
        body = TahminKaydiDetaySerializer(
            record, context={"tekrarlandi": repeated}
        ).data
        return Response(
            body, status=status.HTTP_200_OK if repeated else status.HTTP_201_CREATED
        )


class TahminKaydiDetayi(APIView):
    permission_classes = (IsAuthenticated, AktifTahminKullanicisiMi)

    def get(self, request, pk):
        record = get_object_or_404(tahmin_kaydi_detayi(), pk=pk)
        return Response(TahminKaydiDetaySerializer(record).data)
