from unittest.mock import patch

from rest_framework.test import APIClient

from apps.core.services import SaglikDurumu


def test_saglik_basarili():
    durum = SaglikDurumu("hazir", "backend", "bagli")
    with patch("apps.core.api.views.saglik_durumunu_getir", return_value=durum):
        response = APIClient().get("/api/saglik/")

    assert response.status_code == 200
    assert response.json() == {
        "durum": "hazir",
        "servis": "backend",
        "veritabani": "bagli",
    }


def test_saglik_veritabani_hatasi():
    durum = SaglikDurumu("kullanilamiyor", "backend", "baglanti_yok")
    with patch("apps.core.api.views.saglik_durumunu_getir", return_value=durum):
        response = APIClient().get("/api/saglik/")

    assert response.status_code == 503
    assert response.json()["hata"]["kod"] == "HIZMET_KULLANILAMIYOR"


def test_saglik_desteklenmeyen_yontem():
    response = APIClient().post("/api/saglik/", {}, format="json")
    assert response.status_code == 405
