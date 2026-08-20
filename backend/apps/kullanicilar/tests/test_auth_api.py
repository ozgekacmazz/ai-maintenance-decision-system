import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.kullanicilar.models import Kullanici
from apps.kullanicilar.tokens import kullanici_icin_token_cifti

pytestmark = pytest.mark.django_db
PAROLA = "Auth!Guvenli-Parola-2026"


@pytest.fixture
def auth_user():
    return Kullanici.objects.create_user(username="auth-user", password=PAROLA)


@pytest.fixture
def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/auth/csrf/")
    client.credentials(HTTP_X_CSRFTOKEN=response.data["csrf_token"])
    return client


def login(client, username="auth-user", password=PAROLA):
    return client.post(
        "/api/auth/login/", {"username": username, "password": password}, format="json"
    )


def test_csrf_endpoint_token_ve_cookie_olusturur():
    response = APIClient().get("/api/auth/csrf/")
    assert response.status_code == 200
    assert response.data["csrf_token"]
    assert settings.CSRF_COOKIE_NAME in response.cookies
    assert (
        response["Cache-Control"]
        == "max-age=0, no-cache, no-store, must-revalidate, private"
    )


@pytest.mark.parametrize("endpoint", ["login", "refresh", "logout"])
def test_csrf_olmadan_auth_post_reddedilir(endpoint):
    response = APIClient(enforce_csrf_checks=True).post(
        f"/api/auth/{endpoint}/", {}, format="json"
    )
    assert response.status_code == 403


def test_login_access_ve_guvenli_cookie_dondurur(csrf_client, auth_user):
    response = login(csrf_client)
    assert response.status_code == 200
    assert response.data["access"]
    assert "refresh" not in response.data
    assert "password" not in response.data
    assert response.data["kullanici"] == {
        "id": auth_user.id,
        "username": auth_user.username,
        "rol": Kullanici.Rol.USER,
    }
    cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["path"] == "/api/auth/"
    assert cookie["samesite"] == "Lax"
    assert not cookie["secure"]


def test_yanlis_username_ve_parola_ayni_genel_hatayi_dondurur(csrf_client, auth_user):
    yanlis_user = login(csrf_client, username="olmayan")
    yanlis_parola = login(csrf_client, password="yanlis-parola")
    assert yanlis_user.status_code == yanlis_parola.status_code == 401
    for alan in ("kod", "mesaj", "alanlar"):
        assert yanlis_user.data["hata"][alan] == yanlis_parola.data["hata"][alan]


def test_pasif_kullanici_giris_yapamaz(csrf_client, auth_user):
    auth_user.is_active = False
    auth_user.save(update_fields=("is_active",))
    assert login(csrf_client).status_code == 401


def test_login_throttle_calisir(csrf_client, auth_user, monkeypatch):
    cache.clear()
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "login", "1/min")
    assert login(csrf_client).status_code == 200
    assert login(csrf_client).status_code == 429


def test_refresh_rotation_eski_tokeni_blacklist_eder(csrf_client, auth_user):
    login_response = login(csrf_client)
    eski_cookie = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    response = csrf_client.post("/api/auth/refresh/")
    assert response.status_code == 200
    assert response.data["access"]
    assert "refresh" not in response.data
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value != eski_cookie
    assert BlacklistedToken.objects.count() == 1

    eski_client = APIClient(enforce_csrf_checks=True)
    csrf = eski_client.get("/api/auth/csrf/").data["csrf_token"]
    eski_client.credentials(HTTP_X_CSRFTOKEN=csrf)
    eski_client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = eski_cookie
    assert eski_client.post("/api/auth/refresh/").status_code == 401


def test_refresh_cookie_yok_ve_bozuksa_401(csrf_client):
    assert csrf_client.post("/api/auth/refresh/").status_code == 401
    csrf_client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = "bozuk"
    assert csrf_client.post("/api/auth/refresh/").status_code == 401


def test_pasif_kullanici_refresh_yapamaz(csrf_client, auth_user):
    login(csrf_client)
    auth_user.is_active = False
    auth_user.save(update_fields=("is_active",))
    assert csrf_client.post("/api/auth/refresh/").status_code == 401


def test_logout_blacklist_cookie_silme_ve_idempotency(csrf_client, auth_user):
    login_response = login(csrf_client)
    eski_cookie = login_response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
    response = csrf_client.post("/api/auth/logout/")
    assert response.status_code == 204
    assert response.cookies[settings.JWT_REFRESH_COOKIE_NAME]["max-age"] == 0
    assert BlacklistedToken.objects.count() == 1
    csrf_client.cookies.pop(settings.JWT_REFRESH_COOKIE_NAME, None)
    assert csrf_client.post("/api/auth/logout/").status_code == 204

    csrf_client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = eski_cookie
    assert csrf_client.post("/api/auth/refresh/").status_code == 401


def test_me_access_ile_guvenli_ozet_dondurur(auth_user):
    access, _ = kullanici_icin_token_cifti(auth_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["username"] == auth_user.username
    assert response.data["email"] == auth_user.email
    assert "password" not in response.data
    assert APIClient().get("/api/auth/me/").status_code == 401
    client.credentials(HTTP_AUTHORIZATION="Bearer bozuk")
    assert client.get("/api/auth/me/").status_code == 401


def test_pasif_kullanici_access_ile_me_erisiminden_reddedilir(auth_user):
    access, _ = kullanici_icin_token_cifti(auth_user)
    auth_user.is_active = False
    auth_user.save(update_fields=("is_active",))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/auth/me/").status_code == 401


@pytest.mark.parametrize(
    ("rol", "is_staff", "is_superuser", "beklenen"),
    [
        (Kullanici.Rol.ADMIN, False, False, 200),
        (Kullanici.Rol.USER, False, False, 403),
        (Kullanici.Rol.USER, True, True, 403),
    ],
)
def test_admin_kontrol_server_side_rol_kullanir(rol, is_staff, is_superuser, beklenen):
    kullanici = Kullanici.objects.create_user(
        username=f"kontrol-{rol}-{is_superuser}",
        password=PAROLA,
        rol=rol,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    access, _ = kullanici_icin_token_cifti(kullanici)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/auth/admin-kontrol/").status_code == beklenen


def test_admin_kontrol_tokensiz_401():
    assert APIClient().get("/api/auth/admin-kontrol/").status_code == 401


@pytest.mark.parametrize("payload", [{"is_active": False}, {"rol": "USER"}])
def test_admin_kendi_hesabini_pasife_alip_rolunu_dusuremez(payload):
    admin = Kullanici.objects.create_user(
        username="self-protected-admin", password=PAROLA, rol=Kullanici.Rol.ADMIN
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"/api/auth/kullanicilar/{admin.pk}/", payload, format="json"
    )

    assert response.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active is True
    assert admin.rol == Kullanici.Rol.ADMIN
