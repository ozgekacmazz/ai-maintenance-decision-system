from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bakim.api.pagination import BakimSayfalama
from apps.tahminler import replay_selectors, replay_services, services
from apps.tahminler.api.replay_serializers import (
    AdimSerializer,
    IptalSerializer,
    ReplayDetaySerializer,
    ReplayFiltreSerializer,
    ReplayOgeFiltreSerializer,
    ReplayOgeSerializer,
    ReplayOlusturmaSerializer,
    ReplayOturumuSerializer,
    VersionSerializer,
)
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


class ReplayView(APIView):
    permission_classes = (IsAuthenticated, AktifTahminKullanicisiMi)

    def parse(self, request, serializer_class):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def require_admin(self, request):
        if request.user.rol != request.user.Rol.ADMIN:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Replay işlemi için yönetici yetkisi gereklidir.")

    def detail(self, pk):
        return get_object_or_404(replay_selectors.replay_detayi(), pk=pk)


class ReplayOturumListesi(ReplayView):
    def get(self, request):
        serializer = ReplayFiltreSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        queryset = replay_selectors.replay_oturumlari(serializer.validated_data)
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(queryset, request, self)
        return paginator.get_paginated_response(
            ReplayOturumuSerializer(page, many=True).data
        )

    def post(self, request):
        self.require_admin(request)
        session = replay_services.replay_olustur(
            actor=request.user,
            trace_id=request.trace_id,
            data=self.parse(request, ReplayOlusturmaSerializer),
        )
        return Response(
            ReplayDetaySerializer(self.detail(session.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class ReplayOturumDetayi(ReplayView):
    def get(self, request, pk):
        return Response(ReplayDetaySerializer(self.detail(pk)).data)


class ReplayOgeListesi(ReplayView):
    def get(self, request, pk):
        get_object_or_404(replay_selectors.replay_detayi(), pk=pk)
        serializer = ReplayOgeFiltreSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(
            replay_selectors.replay_ogeleri(pk, serializer.validated_data),
            request,
            self,
        )
        return paginator.get_paginated_response(
            ReplayOgeSerializer(page, many=True).data
        )


class ReplayMutation(ReplayView):
    target = None
    serializer_class = VersionSerializer

    def post(self, request, pk):
        self.require_admin(request)
        data = self.parse(request, self.serializer_class)
        session = replay_services.replay_gecis(
            session_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data["beklenen_version"],
            target=self.target,
            reason=data.get("iptal_nedeni"),
        )
        return Response(ReplayDetaySerializer(self.detail(session.pk)).data)


class ReplayBaslat(ReplayMutation):
    target = "CALISIYOR"


class ReplayDuraklat(ReplayMutation):
    target = "DURAKLATILDI"


class ReplayDevam(ReplayMutation):
    target = "CALISIYOR"


class ReplayIptal(ReplayMutation):
    target = "IPTAL_EDILDI"
    serializer_class = IptalSerializer


class ReplayAdim(ReplayView):
    def post(self, request, pk):
        self.require_admin(request)
        data = self.parse(request, AdimSerializer)
        session = get_object_or_404(replay_selectors.replay_detayi(), pk=pk)
        replay_services.replay_adim(
            session_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data["beklenen_version"],
            batch_size=data.get("batch_boyutu", session.varsayilan_batch_boyutu),
        )
        return Response(ReplayDetaySerializer(self.detail(pk)).data)


class ReplayRetry(ReplayView):
    def post(self, request, pk):
        self.require_admin(request)
        data = self.parse(request, VersionSerializer)
        replay_services.basarisizlari_yeniden_dene(
            session_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data["beklenen_version"],
        )
        return Response(ReplayDetaySerializer(self.detail(pk)).data)
