import json

import pytest
from rest_framework.test import APIClient

from apps.core.openapi import build_openapi_schema
from apps.kullanicilar.models import Kullanici

pytestmark = pytest.mark.django_db


@pytest.fixture
def authenticated_client():
    user = Kullanici.objects.create_user(
        username="schema-admin", rol=Kullanici.Rol.ADMIN
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_schema_and_docs_require_authentication(authenticated_client):
    assert APIClient().get("/api/schema/").status_code == 401
    assert APIClient().get("/api/docs/").status_code == 401
    assert authenticated_client.get("/api/schema/").status_code == 200
    assert authenticated_client.get("/api/docs/").status_code == 200


def test_schema_is_openapi_3_parseable_and_deterministic(authenticated_client):
    first = authenticated_client.get("/api/schema/", HTTP_ACCEPT="application/json")
    second = authenticated_client.get("/api/schema/", HTTP_ACCEPT="application/json")
    first_document = json.loads(first.content)
    second_document = json.loads(second.content)
    assert first_document == second_document == build_openapi_schema()
    assert first_document["openapi"].startswith("3.")


def test_operation_ids_are_unique_and_required_paths_exist():
    schema = build_openapi_schema()
    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert len(operation_ids) == len(set(operation_ids))
    assert {
        "/api/auth/login/",
        "/api/makine-secenekleri/",
        "/api/tahminler/risk/",
        "/api/tahminler/input-domain/",
        "/api/tahminler/kayitlar/{pk}/reddet/",
        "/api/bakim/is-emirleri/{pk}/durum-gecisi/",
        "/api/bakim/is-emirleri/{pk}/oncelik-override/",
        "/api/tahminler/loglari/",
        "/api/tahminler/replay-oturumlari/{pk}/adim/",
    } <= set(schema["paths"])


def test_jwt_error_and_admin_security_contracts():
    schema = build_openapi_schema()
    assert schema["components"]["securitySchemes"]["jwtAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    error = schema["components"]["schemas"]["StandartHata"]["properties"]["hata"]
    assert {"kod", "mesaj", "alanlar", "trace_id"} <= set(error["properties"])
    admin_operation = schema["paths"]["/api/tahminler/loglari/"]["get"]
    assert admin_operation["security"] == [{"jwtAuth": []}]


def test_filter_enums_priority_range_kelvin_and_override_contract():
    schema = build_openapi_schema()
    prediction_parameters = {
        item["name"]: item
        for item in schema["paths"]["/api/tahminler/kayitlar/"]["get"]["parameters"]
    }
    assert prediction_parameters["genel_oncelik"]["schema"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 5,
    }
    log_parameters = {
        item["name"]: item
        for item in schema["paths"]["/api/tahminler/loglari/"]["get"]["parameters"]
    }
    assert "REDDEDILDI" in log_parameters["karar_durumu"]["schema"]["enum"]
    sensor = schema["components"]["schemas"]["SensorRequest"]
    assert sensor["properties"]["hava_sicakligi_k"]["description"].startswith("Kelvin")
    override = schema["components"]["schemas"]["OncelikOverrideRequest"]
    assert {"genel_oncelik", "etkin_oncelik_seviyesi", "beklenen_version"} <= set(
        override["properties"]
    )


def test_replay_metric_contract_has_no_accuracy_and_has_required_metrics():
    metrics = build_openapi_schema()["components"]["schemas"]["ReplayMetrics"]
    assert "accuracy" not in json.dumps(metrics).lower()
    assert {"precision", "recall", "pr_auc", "confusion_matrix"} <= set(
        metrics["properties"]
    )


def test_password_is_write_only_and_never_in_user_response():
    schemas = build_openapi_schema()["components"]["schemas"]
    assert "password" not in schemas["Kullanici"]["properties"]
    password = schemas["LoginRequest"]["properties"]["password"]
    assert password["writeOnly"] is True
