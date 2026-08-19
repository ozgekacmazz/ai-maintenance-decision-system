from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bakim import selectors, services, work_order_selectors, work_order_services
from apps.bakim.api.pagination import BakimSayfalama
from apps.bakim.api.serializers import (
    AktiflikSerializer,
    KuralFiltre,
    KuralOkumaSerializer,
    KuralYazmaSerializer,
    MakineFiltre,
    MakineOkumaSerializer,
    MakineSecenegiSerializer,
    MakineYazmaSerializer,
    ParcaFiltre,
    ParcaOkumaSerializer,
    ParcaYazmaSerializer,
    StokFiltre,
    StokOkumaSerializer,
    StokYazmaSerializer,
)
from apps.bakim.api.work_order_serializers import (
    IsEmriAtamaSerializer,
    IsEmriDetaySerializer,
    IsEmriDurumGecisiSerializer,
    IsEmriFiltreSerializer,
    IsEmriListeSerializer,
    IsEmriOlusturmaSerializer,
    IsEmriOncelikOverrideSerializer,
)
from apps.bakim.permissions import BakimApiIzni
from apps.kullanicilar.api.permissions import UrunAdminiMi
from apps.kullanicilar.models import Kullanici


class AktifIsEmriKullanicisi(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.rol in {Kullanici.Rol.USER, Kullanici.Rol.ADMIN}
        )


class IsEmriView(APIView):
    permission_classes = (IsAuthenticated, AktifIsEmriKullanicisi)

    def parse(self, request, serializer_class):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def detail(self, pk):
        return get_object_or_404(work_order_selectors.is_emri_detayi(), pk=pk)


class IsEmriListesi(IsEmriView):
    def get(self, request):
        serializer = IsEmriFiltreSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        queryset = work_order_selectors.is_emri_listesi(
            filtreler=serializer.validated_data
        )
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(queryset, request, self)
        return paginator.get_paginated_response(
            IsEmriListeSerializer(page, many=True).data
        )

    def post(self, request):
        order, repeated = work_order_services.is_emri_olustur(
            actor=request.user,
            trace_id=request.trace_id,
            veriler=self.parse(request, IsEmriOlusturmaSerializer),
        )
        order = self.detail(order.pk)
        return Response(
            IsEmriDetaySerializer(order, context={"tekrarlandi": repeated}).data,
            status=status.HTTP_200_OK if repeated else status.HTTP_201_CREATED,
        )


class IsEmriDetayi(IsEmriView):
    def get(self, request, pk):
        return Response(IsEmriDetaySerializer(self.detail(pk)).data)


class IsEmriAtama(IsEmriView):
    def post(self, request, pk):
        data = self.parse(request, IsEmriAtamaSerializer)
        work_order_services.is_emri_ata(
            order_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data["beklenen_version"],
            assignee=data["atanan_kullanici"],
            note=data.get("not"),
        )
        return Response(IsEmriDetaySerializer(self.detail(pk)).data)


class IsEmriDurumGecisi(IsEmriView):
    def post(self, request, pk):
        data = self.parse(request, IsEmriDurumGecisiSerializer)
        work_order_services.is_emri_durum_gecisi(
            order_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data.pop("beklenen_version"),
            target=data.pop("hedef_durum"),
            data=data,
        )
        return Response(IsEmriDetaySerializer(self.detail(pk)).data)


class IsEmriOncelikOverride(IsEmriView):
    def post(self, request, pk):
        data = self.parse(request, IsEmriOncelikOverrideSerializer)
        work_order_services.is_emri_oncelik_override(
            order_id=pk,
            actor=request.user,
            trace_id=request.trace_id,
            expected_version=data["beklenen_version"],
            priority=data.get("etkin_oncelik_seviyesi"),
            general_priority=data.get("genel_oncelik"),
            reason=data["override_nedeni"],
        )
        return Response(IsEmriDetaySerializer(self.detail(pk)).data)


class MakineSecenekleri(APIView):
    permission_classes = (IsAuthenticated, BakimApiIzni)

    def get(self, request):
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(
            selectors.makine_secenekleri(), request, self
        )
        return paginator.get_paginated_response(
            MakineSecenegiSerializer(page, many=True).data
        )


class BakimView(APIView):
    permission_classes = (IsAuthenticated, UrunAdminiMi)

    def filtrele(self, request, serializer_class):
        serializer = serializer_class(data=dict(request.query_params.items()))
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def sayfala(self, request, queryset, serializer_class):
        paginator = BakimSayfalama()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)

    def yazma_verisi(self, request, serializer_class, *, partial=False):
        serializer = serializer_class(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class MakineListe(BakimView):
    def get(self, request):
        return self.sayfala(
            request,
            selectors.makineler(
                kullanici=request.user, filtreler=self.filtrele(request, MakineFiltre)
            ),
            MakineOkumaSerializer,
        )

    def post(self, request):
        nesne = services.makine_olustur(
            veriler=self.yazma_verisi(request, MakineYazmaSerializer)
        )
        return Response(
            MakineOkumaSerializer(nesne).data, status=status.HTTP_201_CREATED
        )


class MakineDetay(BakimView):
    def get(self, request, pk):
        return Response(
            MakineOkumaSerializer(
                selectors.makine_getir(kullanici=request.user, kayit_id=pk)
            ).data
        )

    def patch(self, request, pk):
        nesne = selectors.makine_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.makine_guncelle(
            makine=nesne,
            veriler=self.yazma_verisi(request, MakineYazmaSerializer, partial=True),
        )
        return Response(MakineOkumaSerializer(nesne).data)


class MakineAktiflik(BakimView):
    def post(self, request, pk):
        nesne = selectors.makine_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.makine_aktiflik_degistir(
            makine=nesne, aktif=self.yazma_verisi(request, AktiflikSerializer)["aktif"]
        )
        return Response(MakineOkumaSerializer(nesne).data)


class ParcaListe(BakimView):
    def get(self, request):
        return self.sayfala(
            request,
            selectors.parcalar(
                kullanici=request.user, filtreler=self.filtrele(request, ParcaFiltre)
            ),
            ParcaOkumaSerializer,
        )

    def post(self, request):
        nesne = services.parca_olustur(
            veriler=self.yazma_verisi(request, ParcaYazmaSerializer)
        )
        return Response(
            ParcaOkumaSerializer(nesne).data, status=status.HTTP_201_CREATED
        )


class ParcaDetay(BakimView):
    def get(self, request, pk):
        return Response(
            ParcaOkumaSerializer(
                selectors.parca_getir(kullanici=request.user, kayit_id=pk)
            ).data
        )

    def patch(self, request, pk):
        nesne = selectors.parca_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.parca_guncelle(
            parca=nesne,
            veriler=self.yazma_verisi(request, ParcaYazmaSerializer, partial=True),
        )
        return Response(ParcaOkumaSerializer(nesne).data)


class ParcaAktiflik(BakimView):
    def post(self, request, pk):
        nesne = selectors.parca_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.parca_aktiflik_degistir(
            parca=nesne, aktif=self.yazma_verisi(request, AktiflikSerializer)["aktif"]
        )
        return Response(ParcaOkumaSerializer(nesne).data)


class StokListe(BakimView):
    def get(self, request):
        return self.sayfala(
            request,
            selectors.stoklar(
                kullanici=request.user, filtreler=self.filtrele(request, StokFiltre)
            ),
            StokOkumaSerializer,
        )

    def post(self, request):
        nesne = services.stok_olustur(
            veriler=self.yazma_verisi(request, StokYazmaSerializer)
        )
        return Response(StokOkumaSerializer(nesne).data, status=status.HTTP_201_CREATED)


class StokDetay(BakimView):
    def get(self, request, pk):
        return Response(
            StokOkumaSerializer(
                selectors.stok_getir(kullanici=request.user, kayit_id=pk)
            ).data
        )

    def patch(self, request, pk):
        nesne = selectors.stok_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.stok_guncelle(
            stok=nesne,
            veriler=self.yazma_verisi(request, StokYazmaSerializer, partial=True),
        )
        return Response(StokOkumaSerializer(nesne).data)


class KuralListe(BakimView):
    def get(self, request):
        return self.sayfala(
            request,
            selectors.kurallar(
                kullanici=request.user, filtreler=self.filtrele(request, KuralFiltre)
            ),
            KuralOkumaSerializer,
        )

    def post(self, request):
        nesne = services.kural_olustur(
            veriler=self.yazma_verisi(request, KuralYazmaSerializer)
        )
        return Response(
            KuralOkumaSerializer(nesne).data, status=status.HTTP_201_CREATED
        )


class KuralDetay(BakimView):
    def get(self, request, pk):
        return Response(
            KuralOkumaSerializer(
                selectors.kural_getir(kullanici=request.user, kayit_id=pk)
            ).data
        )

    def patch(self, request, pk):
        nesne = selectors.kural_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.kural_guncelle(
            kural=nesne,
            veriler=self.yazma_verisi(request, KuralYazmaSerializer, partial=True),
        )
        return Response(KuralOkumaSerializer(nesne).data)


class KuralAktiflik(BakimView):
    def post(self, request, pk):
        nesne = selectors.kural_getir(kullanici=request.user, kayit_id=pk)
        nesne = services.kural_aktiflik_degistir(
            kural=nesne, aktif=self.yazma_verisi(request, AktiflikSerializer)["aktif"]
        )
        return Response(KuralOkumaSerializer(nesne).data)
