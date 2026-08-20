import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bakim.models import Makine
from apps.bakim.work_order_services import is_emri_olustur
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import BakimKarariSnapshot, TahminKaydi, TahminReddi

pytestmark = pytest.mark.django_db
URL = "/api/tahminler/loglari/"


def _record(user, machine, key, *, priority=None):
    record = TahminKaydi.objects.create(
        makine=machine,
        olusturan=user,
        trace_id=f"trace-{key}",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key=key,
        payload_fingerprint=key.ljust(64, "x"),
        makine_kodu_snapshot=machine.makine_kodu,
        makine_adi_snapshot=machine.ad,
        kritiklik_snapshot=machine.kritiklik,
        sensor_snapshot={},
        risk_orani=0.8,
        risk_uyarisi=True,
        binary_threshold=0.2,
        binary_model_version="v",
        binary_pipeline_version="p",
        failure_type_durum="DEGERLENDIRILDI",
        belirsiz_fiziksel_tip=False,
        aciklanabilirlik_durum="ACIKLANDI",
    )
    BakimKarariSnapshot.objects.create(
        tahmin=record,
        motor_surumu="v",
        teknik_aciliyet_skoru=80,
        tedarik_riski_skoru=20,
        nihai_oncelik_skoru=75,
        oncelik_seviyesi="YUKSEK",
        genel_oncelik=priority,
        genel_oncelik_formul_surumu="v1" if priority else None,
        stok_katsayisi=1 if priority else None,
        ham_genel_oncelik=priority,
        ana_aksiyon="ONCELIKLI_BAKIM_PLANLA",
        karar_guveni="YUKSEK",
    )
    return record


@pytest.fixture
def users_and_machine():
    admin = Kullanici.objects.create_user(username="log-admin", rol="ADMIN")
    user = Kullanici.objects.create_user(username="log-user", rol="USER")
    machine = Makine.objects.create(
        makine_kodu="LOG-M1", ad="Log Presi", tip="Pres", kritiklik=4
    )
    return admin, user, machine


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_admin_log_canonical_states_and_safe_summaries(users_and_machine):
    admin, user, machine = users_and_machine
    pending = _record(user, machine, "pending", priority=None)
    rejected = _record(user, machine, "rejected", priority=3)
    TahminReddi.objects.create(
        tahmin=rejected, reddeden=user, red_nedeni="Yanlış alarm"
    )
    approved = _record(user, machine, "approved", priority=5)
    order, _ = is_emri_olustur(
        actor=admin,
        trace_id="approve",
        veriler={
            "tahmin_kaydi_id": approved.id,
            "idempotency_key": "approved-order",
            "baslik": "Bakım",
            "aciklama": "Kontrol",
        },
    )
    inconsistent = _record(user, machine, "inconsistent", priority=4)
    is_emri_olustur(
        actor=admin,
        trace_id="inconsistent",
        veriler={
            "tahmin_kaydi_id": inconsistent.id,
            "idempotency_key": "inconsistent-order",
            "baslik": "Bakım",
            "aciklama": "Kontrol",
        },
    )
    TahminReddi.objects.create(
        tahmin=inconsistent, reddeden=user, red_nedeni="Çelişkili kayıt"
    )

    response = _client(admin).get(URL)
    by_id = {str(item["id"]): item for item in response.data["results"]}

    assert by_id[str(pending.id)]["karar_durumu"] == "BEKLIYOR"
    assert by_id[str(pending.id)]["karar_veren"] is None
    assert by_id[str(rejected.id)]["karar_durumu"] == "REDDEDILDI"
    assert by_id[str(rejected.id)]["karar_nedeni"] == "Yanlış alarm"
    assert by_id[str(approved.id)]["karar_durumu"] == "ONAYLANDI"
    assert by_id[str(approved.id)]["is_emri_bilgisi"]["id"] == str(order.id)
    assert by_id[str(inconsistent.id)]["karar_durumu"] == "TUTARSIZ"
    assert by_id[str(inconsistent.id)]["karar_veren"] is None
    assert by_id[str(inconsistent.id)]["onay_bilgisi"] is not None
    assert by_id[str(inconsistent.id)]["red_bilgisi"] is not None


def test_admin_permission_filters_validation_and_read_only(users_and_machine):
    admin, user, machine = users_and_machine
    _record(user, machine, "filter", priority=2)

    assert APIClient().get(URL).status_code == 401
    assert _client(user).get(URL).status_code == 403
    response = _client(admin).get(
        URL, {"karar_durumu": "BEKLIYOR", "makine_id": machine.id, "genel_oncelik": 2}
    )
    assert response.status_code == 200 and response.data["count"] == 1
    invalid = _client(admin).get(
        URL, {"baslangic": "2026-08-20", "bitis": "2026-08-19"}
    )
    assert invalid.status_code == 400
    assert invalid.data["hata"]["kod"] == "GECERSIZ_ISTEK"
    for method in (
        _client(admin).post,
        _client(admin).put,
        _client(admin).patch,
        _client(admin).delete,
    ):
        assert method(URL, {}, format="json").status_code == 405


def test_admin_log_query_count_is_bounded(
    users_and_machine, django_assert_max_num_queries
):
    admin, user, machine = users_and_machine
    for index in range(4):
        _record(user, machine, f"query-{index}", priority=index % 5 + 1)
    with django_assert_max_num_queries(5):
        assert _client(admin).get(URL).status_code == 200
