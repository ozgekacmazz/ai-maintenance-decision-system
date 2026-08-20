import pytest
from rest_framework.test import APIClient

from apps.kullanicilar.models import Kullanici

pytestmark = pytest.mark.django_db
GUCLU_PAROLA = "Guclu!Fabrika-2026-Z"


@pytest.fixture
def admin():
    return Kullanici.objects.create_user(
        username="policy-admin", password=GUCLU_PAROLA, rol=Kullanici.Rol.ADMIN
    )


def _client(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


@pytest.mark.parametrize("parola", ["abc", "password", "123456789"])
def test_create_rejects_weak_password_without_creating_user(admin, parola):
    response = _client(admin).post(
        "/api/auth/kullanicilar/",
        {"username": "weak-target", "email": "weak@example.com", "password": parola},
        format="json",
        HTTP_X_TRACE_ID="password-policy-create",
    )

    assert response.status_code == 400
    assert response.data["hata"]["alanlar"]["password"]
    assert response.data["hata"]["trace_id"] == "password-policy-create"
    assert parola not in " ".join(response.data["hata"]["alanlar"]["password"])
    assert not Kullanici.objects.filter(username="weak-target").exists()


def test_create_uses_unsaved_user_for_similarity_and_accepts_strong_password(admin):
    similar = _client(admin).post(
        "/api/auth/kullanicilar/",
        {
            "username": "aysekaya",
            "email": "aysekaya@example.com",
            "password": "aysekaya2026!",
        },
        format="json",
    )
    assert similar.status_code == 400
    assert similar.data["hata"]["alanlar"]["password"]

    accepted = _client(admin).post(
        "/api/auth/kullanicilar/",
        {
            "username": "valid-target",
            "email": "valid@example.com",
            "password": GUCLU_PAROLA,
            "rol": "USER",
        },
        format="json",
    )
    assert accepted.status_code == 201
    user = Kullanici.objects.get(username="valid-target")
    assert user.check_password(GUCLU_PAROLA)
    assert user.password != GUCLU_PAROLA
    assert "password" not in accepted.data


def test_multiple_validator_messages_are_preserved(admin):
    response = _client(admin).post(
        "/api/auth/kullanicilar/",
        {"username": "multi-target", "password": "1234567"},
        format="json",
    )
    assert response.status_code == 400
    assert len(response.data["hata"]["alanlar"]["password"]) >= 2


def test_reset_permissions_rollback_and_success(admin):
    target = Kullanici.objects.create_user(
        username="reset-target", password=GUCLU_PAROLA, rol=Kullanici.Rol.USER
    )
    old_hash = target.password
    url = f"/api/auth/kullanicilar/{target.id}/sifre-sifirla/"

    assert (
        _client().post(url, {"yeni_sifre": GUCLU_PAROLA}, format="json").status_code
        == 401
    )
    assert (
        _client(target)
        .post(url, {"yeni_sifre": GUCLU_PAROLA}, format="json")
        .status_code
        == 403
    )

    rejected = _client(admin).post(
        url, {"yeni_sifre": "password"}, format="json", HTTP_X_TRACE_ID="reset-trace"
    )
    assert rejected.status_code == 400
    assert rejected.data["hata"]["alanlar"]["yeni_sifre"]
    assert rejected.data["hata"]["trace_id"] == "reset-trace"
    target.refresh_from_db()
    assert target.password == old_hash

    new_password = "Baska!Guclu-Parola-2027"
    accepted = _client(admin).post(url, {"yeni_sifre": new_password}, format="json")
    assert accepted.status_code == 200
    assert new_password not in str(accepted.data)
    target.refresh_from_db()
    assert target.check_password(new_password)
    assert target.password != new_password
