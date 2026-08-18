import pytest

from apps.kullanicilar.exceptions import GecersizRolHatasi
from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.selectors import (
    aktif_kullanicilari_listele,
    role_gore_kullanicilari_listele,
    username_ile_kullanici_bul,
)


def test_aktif_kullanicilar_doner(admin_kullanici, normal_kullanici):
    normal_kullanici.is_active = False
    normal_kullanici.save(update_fields=("is_active",))
    assert list(aktif_kullanicilari_listele()) == [admin_kullanici]


def test_rol_filtresi_dogru_calisir(admin_kullanici, normal_kullanici):
    assert list(role_gore_kullanicilari_listele(Kullanici.Rol.ADMIN)) == [
        admin_kullanici
    ]


def test_username_ile_bulma(admin_kullanici):
    assert username_ile_kullanici_bul(admin_kullanici.username) == admin_kullanici
    assert username_ile_kullanici_bul("yok") is None


def test_gecersiz_rol_kontrollu_hata_uretir():
    with pytest.raises(GecersizRolHatasi):
        role_gore_kullanicilari_listele("ROOT")
