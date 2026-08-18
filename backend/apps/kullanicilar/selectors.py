from django.db.models import QuerySet

from apps.kullanicilar.exceptions import GecersizRolHatasi
from apps.kullanicilar.models import Kullanici


def aktif_kullanicilari_listele() -> QuerySet[Kullanici]:
    return Kullanici.objects.filter(is_active=True)


def role_gore_kullanicilari_listele(rol: str) -> QuerySet[Kullanici]:
    if rol not in Kullanici.Rol.values:
        raise GecersizRolHatasi("Geçersiz kullanıcı rolü.")
    return Kullanici.objects.filter(rol=rol)


def username_ile_kullanici_bul(username: str) -> Kullanici | None:
    normalized_username = Kullanici.normalize_username(username)
    return Kullanici.objects.filter(username=normalized_username).first()
