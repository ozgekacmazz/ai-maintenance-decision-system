import json
import logging
import re

import pytest
from django.urls import path
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.core.exceptions import KaynakCakismasiHatasi
from config.urls import urlpatterns as proje_urlpatterns


class GirisTestSerializer(serializers.Serializer):
    username = serializers.CharField()
    profil = serializers.DictField(child=serializers.CharField(), allow_empty=False)


class ValidationTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = GirisTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class NotFoundTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise NotFound


class ConflictTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        raise KaynakCakismasiHatasi


class UnexpectedTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise RuntimeError("cok-gizli-parola /uygulama/gizli/dosya.py")


urlpatterns = proje_urlpatterns + [
    path("api/test/validation/", ValidationTestView.as_view()),
    path("api/test/not-found/", NotFoundTestView.as_view()),
    path("api/test/conflict/", ConflictTestView.as_view()),
    path("api/test/unexpected/", UnexpectedTestView.as_view()),
]


pytestmark = [pytest.mark.urls(__name__), pytest.mark.django_db]
TRACE_RE = re.compile(r"^[0-9a-f-]{36}$")


def test_basarili_api_response_trace_header_tasir():
    response = APIClient().get("/api/saglik/")
    assert response.status_code == 200
    assert TRACE_RE.fullmatch(response["X-Trace-ID"])


def test_gecerli_istemci_trace_id_korunur():
    response = APIClient().get("/api/saglik/", HTTP_X_TRACE_ID="istemci-trace_123")
    assert response["X-Trace-ID"] == "istemci-trace_123"


@pytest.mark.parametrize("tehlikeli", ["satir\nekle", "../ yol", "x" * 65, "<script>"])
def test_gecersiz_trace_id_yeni_uuid_ile_degistirilir(tehlikeli):
    response = APIClient().get("/api/auth/me/", HTTP_X_TRACE_ID=tehlikeli)
    assert response["X-Trace-ID"] != tehlikeli
    assert TRACE_RE.fullmatch(response["X-Trace-ID"])


def test_validation_error_alanlari_ve_trace_eslesmesi():
    response = APIClient().post("/api/test/validation/", {"profil": {}}, format="json")
    assert response.status_code == 400
    hata = response.json()["hata"]
    assert hata["kod"] == "GECERSIZ_ISTEK"
    assert hata["alanlar"]["username"]
    assert hata["alanlar"]["profil"]
    assert hata["trace_id"] == response["X-Trace-ID"]


def test_auth_permission_not_found_conflict_sozlesmesi():
    client = APIClient()
    assert (
        client.get("/api/auth/me/").json()["hata"]["kod"] == "KIMLIK_DOGRULAMA_GEREKLI"
    )
    assert (
        client.get("/api/test/not-found/").json()["hata"]["kod"] == "KAYNAK_BULUNAMADI"
    )
    assert (
        client.post("/api/test/conflict/").json()["hata"]["kod"] == "KAYNAK_CAKISMASI"
    )


def test_beklenmeyen_exception_guvenli_500_ve_guvenli_log(caplog):
    api_logger = logging.getLogger("api.exception")
    api_logger.propagate = True
    caplog.set_level(logging.ERROR)
    try:
        response = APIClient().get("/api/test/unexpected/")
    finally:
        api_logger.propagate = False
    metin = response.content.decode()
    log_metin = " ".join(record.getMessage() for record in caplog.records)
    assert response.status_code == 500
    assert response.json()["hata"]["kod"] == "BEKLENMEYEN_SUNUCU_HATASI"
    assert "cok-gizli-parola" not in metin
    assert "RuntimeError" not in metin
    assert "/uygulama/" not in metin
    assert "cok-gizli-parola" not in log_metin


def test_api_olmayan_admin_html_olarak_kalir():
    response = APIClient().get("/admin/login/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")


def test_request_logu_guvenli_alanlari_tasir(caplog):
    request_logger = logging.getLogger("api.request")
    request_logger.propagate = True
    caplog.set_level(logging.INFO)
    gizli = "asla-loglanmamali"
    try:
        APIClient().post(
            "/api/auth/login/?gizli=query",
            {"username": "credential", "password": gizli},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {gizli}",
            HTTP_COOKIE=f"refresh_token={gizli}",
        )
    finally:
        request_logger.propagate = False
    record = next(record for record in caplog.records if record.name == "api.request")
    assert record.event == "api_request_completed"
    assert record.method == "POST"
    assert record.path == "/api/auth/login/"
    assert record.status_code in {401, 403}
    assert record.duration_ms >= 0
    serialized = json.dumps(record.__dict__, default=str)
    assert gizli not in serialized
    assert "gizli=query" not in serialized
