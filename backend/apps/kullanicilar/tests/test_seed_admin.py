from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.kullanicilar.models import Kullanici

SEED_PAROLA = "Bootstrap!Guvenli-2026"
YENI_PAROLA = "Bootstrap!Yenilendi-2027"


def ortam_hazirla(monkeypatch, *, username="bootstrap-admin", password=SEED_PAROLA):
    monkeypatch.setenv("ADMIN_USERNAME", username)
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    monkeypatch.setenv("ADMIN_EMAIL", "ADMIN@EXAMPLE.COM")


@pytest.mark.django_db
def test_eksik_username_basarisiz_ve_parola_ciktida_yok(monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", SEED_PAROLA)
    with pytest.raises(CommandError) as hata:
        call_command("seed_admin")
    assert "ADMIN_USERNAME" in str(hata.value)
    assert SEED_PAROLA not in str(hata.value)


@pytest.mark.django_db
def test_eksik_password_basarisiz(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(CommandError) as hata:
        call_command("seed_admin")
    assert "ADMIN_PASSWORD" in str(hata.value)


@pytest.mark.django_db
def test_ilk_calisma_guvenli_superuser_olusturur(monkeypatch):
    ortam_hazirla(monkeypatch)
    stdout = StringIO()
    call_command("seed_admin", stdout=stdout)
    kullanici = Kullanici.objects.get(username="bootstrap-admin")
    assert kullanici.rol == Kullanici.Rol.ADMIN
    assert kullanici.is_active and kullanici.is_staff and kullanici.is_superuser
    assert kullanici.email == "ADMIN@example.com"
    assert kullanici.check_password(SEED_PAROLA)
    assert kullanici.password != SEED_PAROLA
    assert SEED_PAROLA not in stdout.getvalue()


@pytest.mark.django_db
def test_ikinci_calisma_duplicate_olusturmaz_ve_parolayi_degistirmez(monkeypatch):
    ortam_hazirla(monkeypatch)
    call_command("seed_admin")
    kullanici = Kullanici.objects.get(username="bootstrap-admin")
    ilk_hash = kullanici.password
    monkeypatch.setenv("ADMIN_PASSWORD", YENI_PAROLA)
    call_command("seed_admin")
    kullanici.refresh_from_db()
    assert Kullanici.objects.filter(username="bootstrap-admin").count() == 1
    assert kullanici.password == ilk_hash
    assert not kullanici.check_password(YENI_PAROLA)


@pytest.mark.django_db
def test_update_password_mevcut_parolayi_degistirir(monkeypatch):
    ortam_hazirla(monkeypatch)
    call_command("seed_admin")
    monkeypatch.setenv("ADMIN_PASSWORD", YENI_PAROLA)
    stdout = StringIO()
    call_command("seed_admin", update_password=True, stdout=stdout)
    kullanici = Kullanici.objects.get(username="bootstrap-admin")
    assert kullanici.check_password(YENI_PAROLA)
    assert not kullanici.check_password(SEED_PAROLA)
    assert YENI_PAROLA not in stdout.getvalue()


@pytest.mark.django_db
def test_mevcut_kullanici_bootstrap_yetkilerine_getirilir(monkeypatch):
    Kullanici.objects.create_user(
        username="bootstrap-admin",
        password=SEED_PAROLA,
        rol=Kullanici.Rol.USER,
        is_active=False,
    )
    ortam_hazirla(monkeypatch)
    call_command("seed_admin")
    kullanici = Kullanici.objects.get(username="bootstrap-admin")
    assert kullanici.rol == Kullanici.Rol.ADMIN
    assert kullanici.is_active and kullanici.is_staff and kullanici.is_superuser


@pytest.mark.django_db
def test_zayif_parola_kullanici_birakmaz(monkeypatch):
    ortam_hazirla(monkeypatch, username="transaction-test", password="123")
    with pytest.raises(CommandError):
        call_command("seed_admin")
    assert not Kullanici.objects.filter(username="transaction-test").exists()
