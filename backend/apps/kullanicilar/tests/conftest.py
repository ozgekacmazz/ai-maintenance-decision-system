import pytest

from apps.kullanicilar.models import Kullanici


@pytest.fixture
def admin_kullanici(db):
    return Kullanici.objects.create_user(
        username="urun-admin",
        password="CokGuclu!Parola-2026",
        rol=Kullanici.Rol.ADMIN,
    )


@pytest.fixture
def normal_kullanici(db):
    return Kullanici.objects.create_user(
        username="urun-user",
        password="CokGuclu!Parola-2026",
        rol=Kullanici.Rol.USER,
    )
