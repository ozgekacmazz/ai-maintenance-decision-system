from unittest.mock import patch

import numpy as np
import pytest
from rest_framework.test import APIClient

from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.services import MODEL_VERSION, YukluModel

URL = "/api/tahminler/risk/"
VALID = {
    "urun_tipi": "L",
    "hava_sicakligi_k": 298.1,
    "proses_sicakligi_k": 308.6,
    "donus_hizi_rpm": 1551,
    "tork_nm": 42.8,
    "takim_asinmasi_dk": 0,
}
RESULT = {
    "risk_orani": 0.7842,
    "risk_uyarisi": True,
    "threshold": 0.22958333333333336,
    "model_version": MODEL_VERSION,
    "pipeline_version": "1.0.0",
    "ariza_tipi_degerlendirmesi": {
        "durum": "DEGERLENDIRILDI",
        "model_version": "failure-type-1.0.0",
        "pipeline_version": "1.0.0",
        "guvenilir_adaylar": [],
        "deneysel_sinyaller": [],
        "belirsiz_fiziksel_tip": True,
    },
}


class BinaryPipeline:
    classes_ = np.asarray((0, 1))

    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, frame):
        return np.asarray([[1 - self.probability, self.probability]])


@pytest.fixture
def client(db):
    return APIClient()


def authenticated(client, role=Kullanici.Rol.USER, active=True):
    user = Kullanici.objects.create_user(
        username=f"{role.lower()}-{active}",
        password="unused",
        rol=role,
        is_active=active,
    )
    client.force_authenticate(user)
    return client


def test_anonymous_request_is_401(client):
    assert client.post(URL, VALID, format="json").status_code == 401


@pytest.mark.parametrize("role", [Kullanici.Rol.USER, Kullanici.Rol.ADMIN])
def test_active_roles_can_predict(client, role):
    authenticated(client, role)
    with patch(
        "apps.tahminler.services.hiyerarsik_risk_tahmini_yap", return_value=RESULT
    ):
        response = client.post(URL, VALID, format="json", HTTP_X_TRACE_ID="test-trace")
    assert response.status_code == 200
    assert response.data == RESULT
    assert response["X-Trace-ID"] == "test-trace"


def test_inactive_user_is_rejected(client):
    authenticated(client, active=False)
    assert client.post(URL, VALID, format="json").status_code == 403


@pytest.mark.parametrize("field", list(VALID))
def test_every_required_field_is_required(client, field):
    authenticated(client)
    payload = {key: value for key, value in VALID.items() if key != field}
    response = client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert field in response.data["hata"]["alanlar"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("urun_tipi", "X"),
        ("tork_nm", -1),
        ("donus_hizi_rpm", 0),
        ("donus_hizi_rpm", -1),
        ("takim_asinmasi_dk", -1),
        ("tork_nm", True),
    ],
)
def test_invalid_sensor_values_are_rejected(client, field, value):
    authenticated(client)
    response = client.post(URL, {**VALID, field: value}, format="json")
    assert response.status_code == 400
    assert field in response.data["hata"]["alanlar"]


@pytest.mark.parametrize("invalid_literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_numbers_are_rejected(client, invalid_literal):
    authenticated(client)
    body = (
        '{"urun_tipi":"L","hava_sicakligi_k":'
        + invalid_literal
        + ',"proses_sicakligi_k":308.6,"donus_hizi_rpm":1551,'
        '"tork_nm":42.8,"takim_asinmasi_dk":0}'
    )
    response = client.generic("POST", URL, body, content_type="application/json")
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["makine_arizasi", "machine_id", "mekanik_guc_w"])
def test_unexpected_and_leakage_fields_are_rejected(client, field):
    authenticated(client)
    response = client.post(URL, {**VALID, field: 1}, format="json")
    assert response.status_code == 400
    assert field in response.data["hata"]["alanlar"]


def test_model_failure_is_safe_503_with_matching_trace(client):
    authenticated(client)
    with patch(
        "apps.tahminler.services.hiyerarsik_risk_tahmini_yap",
        side_effect=ModelHizmetiHatasi(),
    ):
        response = client.post(URL, VALID, format="json", HTTP_X_TRACE_ID="model-trace")
    assert response.status_code == 503
    assert response.data["hata"]["kod"] == "MODEL_HIZMETI_KULLANILAMIYOR"
    assert response.data["hata"]["trace_id"] == response["X-Trace-ID"] == "model-trace"
    serialized = str(response.data).lower()
    assert "checksum" not in serialized
    assert ".joblib" not in serialized
    assert "traceback" not in serialized


def test_low_risk_succeeds_when_failure_type_model_is_missing(client):
    authenticated(client)
    binary = YukluModel(BinaryPipeline(0.1), 0.6, MODEL_VERSION, "1.0.0")
    with (
        patch("apps.tahminler.services.modeli_getir", return_value=binary),
        patch(
            "apps.tahminler.services.ariza_tipi_modeli_getir",
            side_effect=AssertionError("çağrılmamalı"),
        ) as failure_loader,
    ):
        response = client.post(URL, VALID, format="json")
    assert response.status_code == 200
    assert response.data["ariza_tipi_degerlendirmesi"]["durum"] == "RISK_ESIK_ALTINDA"
    failure_loader.assert_not_called()


def test_high_risk_missing_failure_type_model_is_safe_503(client):
    authenticated(client)
    binary = YukluModel(BinaryPipeline(0.9), 0.6, MODEL_VERSION, "1.0.0")
    with (
        patch("apps.tahminler.services.modeli_getir", return_value=binary),
        patch(
            "apps.tahminler.services.ariza_tipi_modeli_getir",
            side_effect=ModelHizmetiHatasi(),
        ),
    ):
        response = client.post(
            URL, VALID, format="json", HTTP_X_TRACE_ID="failure-type-trace"
        )
    assert response.status_code == 503
    assert response.data["hata"]["kod"] == "MODEL_HIZMETI_KULLANILAMIYOR"
    assert response.data["hata"]["trace_id"] == response["X-Trace-ID"]
