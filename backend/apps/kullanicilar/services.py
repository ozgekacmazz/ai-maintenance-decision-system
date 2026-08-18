from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.kullanicilar.exceptions import (
    GecersizParolaHatasi,
    GecersizRolHatasi,
    KendiHesabiniPasifeAlmaHatasi,
    TekrarlananKullaniciAdiHatasi,
    YetkisizKullaniciYonetimiHatasi,
)
from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.policies import kullanici_yonetebilir_mi


def _yetkiyi_dogrula(islemi_yapan: Kullanici) -> None:
    if not kullanici_yonetebilir_mi(islemi_yapan):
        raise YetkisizKullaniciYonetimiHatasi(
            "Bu kullanıcı, kullanıcı yönetimi işlemi yapamaz."
        )


def _rolu_dogrula(rol: str) -> None:
    if rol not in Kullanici.Rol.values:
        raise GecersizRolHatasi("Geçersiz kullanıcı rolü.")


def _parolayi_dogrula(parola: str, kullanici: Kullanici) -> None:
    if not parola:
        raise GecersizParolaHatasi("Parola zorunludur.")
    try:
        password_validation.validate_password(parola, user=kullanici)
    except ValidationError as exc:
        raise GecersizParolaHatasi("Parola güvenlik kurallarını karşılamıyor.") from exc


@transaction.atomic
def kullanici_olustur(
    *,
    islemi_yapan: Kullanici,
    username: str,
    parola: str,
    email: str = "",
    rol: str = Kullanici.Rol.USER,
) -> Kullanici:
    _yetkiyi_dogrula(islemi_yapan)
    if not username or not username.strip():
        raise ValueError("Kullanıcı adı zorunludur.")
    _rolu_dogrula(rol)

    username = Kullanici.normalize_username(username.strip())
    email = Kullanici.objects.normalize_email(email)
    aday = Kullanici(username=username, email=email, rol=rol)
    _parolayi_dogrula(parola, aday)

    try:
        return Kullanici.objects.create_user(
            username=username, email=email, password=parola, rol=rol
        )
    except IntegrityError as exc:
        raise TekrarlananKullaniciAdiHatasi(
            "Bu kullanıcı adı zaten kullanılıyor."
        ) from exc


@transaction.atomic
def kullanici_pasife_al(*, islemi_yapan: Kullanici, kullanici: Kullanici) -> Kullanici:
    _yetkiyi_dogrula(islemi_yapan)
    if islemi_yapan.pk == kullanici.pk:
        raise KendiHesabiniPasifeAlmaHatasi("Yönetici kendi hesabını pasife alamaz.")
    if kullanici.is_active:
        kullanici.is_active = False
        kullanici.save(update_fields=("is_active",))
    return kullanici


@transaction.atomic
def kullanici_aktiflestir(
    *, islemi_yapan: Kullanici, kullanici: Kullanici
) -> Kullanici:
    _yetkiyi_dogrula(islemi_yapan)
    if not kullanici.is_active:
        kullanici.is_active = True
        kullanici.save(update_fields=("is_active",))
    return kullanici


@transaction.atomic
def kullanici_parolasini_guncelle(
    *, islemi_yapan: Kullanici, kullanici: Kullanici, yeni_parola: str
) -> Kullanici:
    _yetkiyi_dogrula(islemi_yapan)
    _parolayi_dogrula(yeni_parola, kullanici)
    kullanici.set_password(yeni_parola)
    kullanici.save(update_fields=("password",))
    return kullanici
