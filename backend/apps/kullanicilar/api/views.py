from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.exceptions import KimlikDogrulamaApiHatasi
from apps.kullanicilar.api.permissions import UrunAdminiMi
from apps.kullanicilar.api.serializers import (
    GirisSerializer,
    KullaniciGuncellemeSerializer,
    KullaniciOlusturmaSerializer,
    KullaniciOzetiSerializer,
    KullaniciYonetimSerializer,
    SifreGuncellemeSerializer,
)
from apps.kullanicilar.auth_services import (
    KimlikDogrulamaHatasi,
    giris_yap,
    refresh_token_iptal_et,
    refresh_token_yenile,
)
from apps.kullanicilar.cookies import refresh_cookie_ayarla, refresh_cookie_sil
from apps.kullanicilar.models import Kullanici


def _kullanici_ozeti(kullanici, *, email=False):
    alanlar = {"id": kullanici.id, "username": kullanici.username, "rol": kullanici.rol}
    if email:
        alanlar["email"] = kullanici.email
    return KullaniciOzetiSerializer(alanlar).data


@method_decorator([ensure_csrf_cookie, never_cache], name="dispatch")
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator([csrf_protect, never_cache], name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = GirisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            kullanici, access, refresh = giris_yap(**serializer.validated_data)
        except KimlikDogrulamaHatasi as exc:
            raise KimlikDogrulamaApiHatasi from exc
        response = Response(
            {"access": access, "kullanici": _kullanici_ozeti(kullanici)}
        )
        refresh_cookie_ayarla(response, refresh)
        return response


@method_decorator([csrf_protect, never_cache], name="dispatch")
class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            raise KimlikDogrulamaApiHatasi
        try:
            access, refresh = refresh_token_yenile(raw_refresh)
        except KimlikDogrulamaHatasi as exc:
            raise KimlikDogrulamaApiHatasi from exc
        response = Response({"access": access})
        refresh_cookie_ayarla(response, refresh)
        return response


@method_decorator([csrf_protect, never_cache], name="dispatch")
class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token_iptal_et(request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        refresh_cookie_sil(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_kullanici_ozeti(request.user, email=True))


class AdminKontrolView(APIView):
    permission_classes = [IsAuthenticated, UrunAdminiMi]

    def get(self, request):
        return Response({"durum": "izinli", "rol": request.user.rol})


class AdminKullaniciListesi(APIView):
    permission_classes = [IsAuthenticated, UrunAdminiMi]

    def get(self, request):
        kullanicilar = Kullanici.objects.all().order_by("-date_joined")
        return Response(KullaniciYonetimSerializer(kullanicilar, many=True).data)

    def post(self, request):
        serializer = KullaniciOlusturmaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            KullaniciYonetimSerializer(user).data, status=status.HTTP_201_CREATED
        )


class AdminKullaniciDetayi(APIView):
    permission_classes = [IsAuthenticated, UrunAdminiMi]

    def patch(self, request, pk):
        user = get_object_or_404(Kullanici, pk=pk)
        if user.pk == request.user.pk:
            if request.data.get("is_active") is False:
                raise ValidationError(
                    {"is_active": ["Yönetici kendi hesabını pasife alamaz."]}
                )
            if request.data.get("rol") not in (None, Kullanici.Rol.ADMIN):
                raise ValidationError(
                    {"rol": ["Yönetici kendi ADMIN rolünü kaldıramaz."]}
                )
        serializer = KullaniciGuncellemeSerializer(
            user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(KullaniciYonetimSerializer(user).data)


class AdminKullaniciSifreSifirla(APIView):
    permission_classes = [IsAuthenticated, UrunAdminiMi]

    def post(self, request, pk):
        user = get_object_or_404(Kullanici, pk=pk)
        serializer = SifreGuncellemeSerializer(
            data=request.data, context={"kullanici": user}
        )
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["yeni_sifre"])
        user.save()
        return Response({"mesaj": "Parola başarıyla güncellendi."})
