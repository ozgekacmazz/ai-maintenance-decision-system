import pytest

from apps.kullanicilar.exceptions import (
    GecersizParolaHatasi,
    GecersizRolHatasi,
    KendiHesabiniPasifeAlmaHatasi,
    TekrarlananKullaniciAdiHatasi,
    YetkisizKullaniciYonetimiHatasi,
)
from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.services import (
    kullanici_aktiflestir,
    kullanici_olustur,
    kullanici_parolasini_guncelle,
    kullanici_pasife_al,
)

GUCLU_PAROLA = "Benzersiz!Parola-2026"


def test_admin_varsayilan_user_olusturabilir(admin_kullanici):
    kullanici = kullanici_olustur(
        islemi_yapan=admin_kullanici,
        username="yeni-user",
        email="TEST@EXAMPLE.COM",
        parola=GUCLU_PAROLA,
    )
    assert kullanici.rol == Kullanici.Rol.USER
    assert kullanici.email == "TEST@example.com"
    assert kullanici.check_password(GUCLU_PAROLA)
    assert kullanici.password != GUCLU_PAROLA


def test_admin_rolunde_kullanici_olusturulabilir(admin_kullanici):
    kullanici = kullanici_olustur(
        islemi_yapan=admin_kullanici,
        username="ikinci-admin",
        parola=GUCLU_PAROLA,
        rol=Kullanici.Rol.ADMIN,
    )
    assert kullanici.rol == Kullanici.Rol.ADMIN
    assert not kullanici.is_staff


@pytest.mark.parametrize("pasif", [False, True])
def test_user_ve_pasif_admin_kullanici_olusturamaz(
    normal_kullanici, admin_kullanici, pasif
):
    islemi_yapan = admin_kullanici if pasif else normal_kullanici
    if pasif:
        admin_kullanici.is_active = False
    with pytest.raises(YetkisizKullaniciYonetimiHatasi):
        kullanici_olustur(
            islemi_yapan=islemi_yapan,
            username="yasak",
            parola=GUCLU_PAROLA,
        )


def test_zayif_parola_reddedilir(admin_kullanici):
    with pytest.raises(GecersizParolaHatasi):
        kullanici_olustur(islemi_yapan=admin_kullanici, username="zayif", parola="123")


def test_gecersiz_rol_reddedilir(admin_kullanici):
    with pytest.raises(GecersizRolHatasi):
        kullanici_olustur(
            islemi_yapan=admin_kullanici,
            username="rol-test",
            parola=GUCLU_PAROLA,
            rol="ROOT",
        )


def test_duplicate_username_servis_hatasina_donusur(admin_kullanici, normal_kullanici):
    with pytest.raises(TekrarlananKullaniciAdiHatasi):
        kullanici_olustur(
            islemi_yapan=admin_kullanici,
            username=normal_kullanici.username,
            parola=GUCLU_PAROLA,
        )


def test_admin_kullaniciyi_idempotent_pasife_alabilir(
    admin_kullanici, normal_kullanici
):
    eski_hash = normal_kullanici.password
    kullanici_pasife_al(islemi_yapan=admin_kullanici, kullanici=normal_kullanici)
    kullanici_pasife_al(islemi_yapan=admin_kullanici, kullanici=normal_kullanici)
    normal_kullanici.refresh_from_db()
    assert not normal_kullanici.is_active
    assert normal_kullanici.password == eski_hash


def test_admin_kullaniciyi_idempotent_aktiflestirebilir(
    admin_kullanici, normal_kullanici
):
    normal_kullanici.is_active = False
    normal_kullanici.save(update_fields=("is_active",))
    kullanici_aktiflestir(islemi_yapan=admin_kullanici, kullanici=normal_kullanici)
    kullanici_aktiflestir(islemi_yapan=admin_kullanici, kullanici=normal_kullanici)
    normal_kullanici.refresh_from_db()
    assert normal_kullanici.is_active


def test_user_aktiflik_degistiremez(normal_kullanici, admin_kullanici):
    with pytest.raises(YetkisizKullaniciYonetimiHatasi):
        kullanici_pasife_al(islemi_yapan=normal_kullanici, kullanici=admin_kullanici)
    with pytest.raises(YetkisizKullaniciYonetimiHatasi):
        kullanici_aktiflestir(islemi_yapan=normal_kullanici, kullanici=admin_kullanici)


def test_admin_kendi_hesabini_pasife_alamaz(admin_kullanici):
    with pytest.raises(KendiHesabiniPasifeAlmaHatasi):
        kullanici_pasife_al(islemi_yapan=admin_kullanici, kullanici=admin_kullanici)


def test_admin_parolayi_guncelleyebilir(admin_kullanici, normal_kullanici):
    eski_parola = "CokGuclu!Parola-2026"
    eski_rol = normal_kullanici.rol
    kullanici_parolasini_guncelle(
        islemi_yapan=admin_kullanici,
        kullanici=normal_kullanici,
        yeni_parola=GUCLU_PAROLA,
    )
    normal_kullanici.refresh_from_db()
    assert normal_kullanici.check_password(GUCLU_PAROLA)
    assert not normal_kullanici.check_password(eski_parola)
    assert normal_kullanici.rol == eski_rol
    assert normal_kullanici.is_active


def test_zayif_parola_guncellemesi_reddedilir(admin_kullanici, normal_kullanici):
    with pytest.raises(GecersizParolaHatasi):
        kullanici_parolasini_guncelle(
            islemi_yapan=admin_kullanici,
            kullanici=normal_kullanici,
            yeni_parola="123",
        )


def test_user_parola_guncelleyemez(normal_kullanici, admin_kullanici):
    with pytest.raises(YetkisizKullaniciYonetimiHatasi):
        kullanici_parolasini_guncelle(
            islemi_yapan=normal_kullanici,
            kullanici=admin_kullanici,
            yeni_parola=GUCLU_PAROLA,
        )
