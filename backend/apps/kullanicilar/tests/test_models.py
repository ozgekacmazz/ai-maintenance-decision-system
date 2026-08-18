import pytest
from django.contrib.auth import get_user_model

from apps.kullanicilar.models import Kullanici

pytestmark = pytest.mark.django_db


def test_kullanici_modeli_ayarlardan_cozulur():
    assert get_user_model() is Kullanici


def test_varsayilan_rol_user():
    kullanici = Kullanici.objects.create_user(
        username="user", password="guvenli-parola"
    )
    assert kullanici.rol == Kullanici.Rol.USER


def test_admin_rolu_saklanabilir():
    kullanici = Kullanici.objects.create_user(
        username="admin-rol", password="guvenli-parola", rol=Kullanici.Rol.ADMIN
    )
    kullanici.refresh_from_db()
    assert kullanici.rol == Kullanici.Rol.ADMIN
    assert kullanici.is_staff is False
    assert kullanici.is_superuser is False


def test_parola_duz_metin_saklanmaz():
    parola = "guvenli-parola"
    kullanici = Kullanici.objects.create_user(username="hash-test", password=parola)
    assert kullanici.password != parola
    assert kullanici.check_password(parola)
