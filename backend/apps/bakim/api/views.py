from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bakim import selectors, services
from apps.bakim.api.pagination import BakimSayfalama
from apps.bakim.api.serializers import (
    AktiflikSerializer,
    KuralFiltre,
    KuralOkumaSerializer,
    KuralYazmaSerializer,
    MakineFiltre,
    MakineOkumaSerializer,
    MakineYazmaSerializer,
    ParcaFiltre,
    ParcaOkumaSerializer,
    ParcaYazmaSerializer,
    StokFiltre,
    StokOkumaSerializer,
    StokYazmaSerializer,
)
from apps.bakim.permissions import BakimApiIzni


class BakimView(APIView):
    permission_classes = (IsAuthenticated, BakimApiIzni)

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
