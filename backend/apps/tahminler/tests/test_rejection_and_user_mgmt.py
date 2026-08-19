import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.bakim.models import Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.record_services import tahmin_kaydi_olustur


@pytest.mark.django_db
def test_admin_user_management_crud():
    client = APIClient()
    admin_user = Kullanici.objects.create_superuser(
        username="admin_test",
        email="admin@test.local",
        password="Password123!",
        rol=Kullanici.Rol.ADMIN,
    )
    normal_user = Kullanici.objects.create_user(
        username="user_test",
        email="user@test.local",
        password="Password123!",
        rol=Kullanici.Rol.USER,
    )

    # Non-admin 403 test
    client.force_authenticate(user=normal_user)
    res = client.get("/api/auth/kullanicilar/")
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Admin list test
    client.force_authenticate(user=admin_user)
    res = client.get("/api/auth/kullanicilar/")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) >= 2

    # Create user test
    res = client.post(
        "/api/auth/kullanicilar/",
        {
            "username": "new_op",
            "email": "new_op@test.local",
            "password": "Yeni.Op!Guclu-2026",
            "rol": "USER",
            "is_active": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["username"] == "new_op"

    # Toggle active state test
    created_id = res.data["id"]
    res = client.patch(
        f"/api/auth/kullanicilar/{created_id}/", {"is_active": False}, format="json"
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.data["is_active"] is False

    # Password reset test
    res = client.post(
        f"/api/auth/kullanicilar/{created_id}/sifre-sifirla/",
        {"yeni_sifre": "NewPassword123!"},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_prediction_rejection_workflow():
    client = APIClient()
    admin = Kullanici.objects.create_superuser(
        username="admin_rej",
        email="admin_rej@test.local",
        password="Password123!",
        rol=Kullanici.Rol.ADMIN,
    )
    machine = Makine.objects.create(
        makine_kodu="M-REJ-01", ad="Rejection Test Machine", kritiklik=4, aktif=True
    )
    prediction, _ = tahmin_kaydi_olustur(
        kullanici=admin,
        trace_id="trace-rej-01",
        veriler={
            "makine_id": machine.id,
            "olcum_zamani": timezone.now(),
            "kaynak": "MANUEL",
            "idempotency_key": "rej-ikey-01",
            "sensor_verisi": {
                "urun_tipi": "M",
                "hava_sicakligi_k": 304.5,
                "proses_sicakligi_k": 315.8,
                "donus_hizi_rpm": 1350,
                "tork_nm": 62.0,
                "takim_asinmasi_dk": 210,
            },
        },
    )

    client.force_authenticate(user=admin)

    # Reject prediction
    res = client.post(
        f"/api/tahminler/kayitlar/{prediction.id}/reddet/",
        {"red_nedeni": "Yanlış alarm"},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["red_bilgisi"]["reddeden"] == "admin_rej"
    assert res.data["red_bilgisi"]["red_nedeni"] == "Yanlış alarm"

    # Attempt work order creation on rejected prediction -> expects HTTP 409 Conflict
    res_wo = client.post(
        "/api/bakim/is-emirleri/",
        {
            "tahmin_kaydi_id": str(prediction.id),
            "baslik": "Rejected Prediction WO",
            "aciklama": "Should fail",
            "idempotency_key": "wo-rej-fail-key",
        },
        format="json",
    )
    assert res_wo.status_code == status.HTTP_409_CONFLICT
    assert "TAHMIN_REDDEDILMIS" in str(res_wo.data)
