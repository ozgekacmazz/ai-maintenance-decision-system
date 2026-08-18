from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.kullanicilar.tokens import kullanici_icin_token_cifti


class KimlikDogrulamaHatasi(Exception):
    pass


def giris_yap(*, username: str, password: str):
    kullanici = authenticate(username=username, password=password)
    if kullanici is None or not kullanici.is_active:
        raise KimlikDogrulamaHatasi("Kullanıcı adı veya parola hatalı.")
    access, refresh = kullanici_icin_token_cifti(kullanici)
    return kullanici, access, refresh


def refresh_token_yenile(raw_refresh: str):
    try:
        eski_refresh = RefreshToken(raw_refresh)
        user_id = eski_refresh["user_id"]
        kullanici = get_user_model().objects.get(pk=user_id, is_active=True)
        eski_refresh.blacklist()
    except (TokenError, get_user_model().DoesNotExist, KeyError) as exc:
        raise KimlikDogrulamaHatasi("Oturum yenilenemedi.") from exc
    access, yeni_refresh = kullanici_icin_token_cifti(kullanici)
    return access, yeni_refresh


def refresh_token_iptal_et(raw_refresh: str | None) -> None:
    if not raw_refresh:
        return
    try:
        RefreshToken(raw_refresh).blacklist()
    except TokenError:
        pass
