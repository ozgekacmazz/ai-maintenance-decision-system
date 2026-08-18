from django.contrib.auth.models import AnonymousUser

from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.policies import aktif_admin_mi, kullanici_yonetebilir_mi


def test_aktif_admin_kullanici_yonetebilir(admin_kullanici):
    assert kullanici_yonetebilir_mi(admin_kullanici)


def test_user_kullanici_yonetemez(normal_kullanici):
    assert not kullanici_yonetebilir_mi(normal_kullanici)


def test_pasif_admin_kullanici_yonetemez(admin_kullanici):
    admin_kullanici.is_active = False
    assert not aktif_admin_mi(admin_kullanici)


def test_none_ve_anonim_kullanici_yonetemez():
    assert not kullanici_yonetebilir_mi(None)
    assert not kullanici_yonetebilir_mi(AnonymousUser())


def test_urun_admin_kontrolu_staff_olmaya_bagli_degil(admin_kullanici):
    assert admin_kullanici.is_staff is False
    assert kullanici_yonetebilir_mi(admin_kullanici)


def test_superuser_urun_rolunun_yerine_gecmez(normal_kullanici):
    normal_kullanici.is_superuser = True
    assert normal_kullanici.rol == Kullanici.Rol.USER
    assert not kullanici_yonetebilir_mi(normal_kullanici)
