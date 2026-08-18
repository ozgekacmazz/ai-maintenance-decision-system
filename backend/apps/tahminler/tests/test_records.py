from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bakim.models import ArizaParcaKurali, Makine, Parca, Stok
from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    ErpSnapshot,
    ShapEtkisiSnapshot,
    TahminKaydi,
)
from apps.tahminler.record_services import payload_fingerprint
from apps.tahminler.services import _ozellikleri_hazirla

pytestmark = pytest.mark.django_db

URL = "/api/tahminler/kayitlar/"
SENSOR = {
    "urun_tipi": "L",
    "hava_sicakligi_k": 298.1,
    "proses_sicakligi_k": 308.6,
    "donus_hizi_rpm": 1551,
    "tork_nm": 42.8,
    "takim_asinmasi_dk": 0,
}


def explanation(target):
    return {
        "target": target,
        "output_space": "probability",
        "base_value": 0.1,
        "ilk_etkiler": [
            {
                "feature": "tork_nm",
                "gorunen_ad": "Tork",
                "original_feature_value": 42.8,
                "model_feature_value": 42.8,
                "birim": "Nm",
                "shap_value": 0.2,
                "yon": "ARTIRIR",
            }
        ],
    }


def result(*, high=True):
    candidates = []
    signals = []
    if high:
        candidates = [
            {
                "kod": "HDF",
                "olasilik": 0.8,
                "threshold": 0.5,
                "esik_asildi": True,
                "guven_durumu": "GUVENILIR",
                "operasyonel_kullanima_uygun": True,
                "aciklama": explanation("HDF"),
            }
        ]
        signals = [
            {
                "kod": "TWF",
                "olasilik": 0.7,
                "threshold": 0.6,
                "esik_asildi": True,
                "guven_durumu": "YETERSIZ_DESTEK",
                "operasyonel_kullanima_uygun": False,
                "aciklama": explanation("TWF"),
            }
        ]
    return {
        "risk_orani": 0.8 if high else 0.1,
        "risk_uyarisi": high,
        "threshold": 0.2,
        "model_version": "binary-1",
        "pipeline_version": "1",
        "ariza_tipi_degerlendirmesi": {
            "durum": "DEGERLENDIRILDI" if high else "RISK_ESIK_ALTINDA",
            "model_version": "failure-1" if high else None,
            "pipeline_version": "1" if high else None,
            "guvenilir_adaylar": candidates,
            "deneysel_sinyaller": signals,
            "belirsiz_fiziksel_tip": high,
        },
        "aciklanabilirlik": {
            "durum": "ACIKLANDI" if high else "RISK_ESIK_ALTINDA",
            "risk_aciklamasi": explanation("machine_failure") if high else None,
        },
    }


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(client):
    value = Kullanici.objects.create_user(username="operator", password="unused")
    client.force_authenticate(value)
    return value


@pytest.fixture
def machine():
    return Makine.objects.create(makine_kodu="M-1", ad="CNC", tip="Kesim", kritiklik=5)


def payload(machine, key="reading-1"):
    return {
        "makine_id": machine.pk,
        "olcum_zamani": timezone.now().isoformat(),
        "kaynak": "MANUEL",
        "idempotency_key": key,
        "sensor_verisi": deepcopy(SENSOR),
    }


def record_values(user, machine, **overrides):
    values = {
        "makine": machine,
        "olusturan": user,
        "trace_id": "t",
        "kaynak": "MANUEL",
        "olcum_zamani": timezone.now(),
        "idempotency_key": "k",
        "payload_fingerprint": "a" * 64,
        "makine_kodu_snapshot": "M-1",
        "makine_adi_snapshot": "CNC",
        "kritiklik_snapshot": 5,
        "sensor_snapshot": SENSOR,
        "risk_orani": 0.1,
        "risk_uyarisi": False,
        "binary_threshold": 0.2,
        "binary_model_version": "v",
        "binary_pipeline_version": "p",
        "failure_type_durum": "LOW",
        "belirsiz_fiziksel_tip": False,
        "aciklanabilirlik_durum": "LOW",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("role", [Kullanici.Rol.USER, Kullanici.Rol.ADMIN])
def test_active_roles_create_persistent_prediction(client, machine, role):
    user = Kullanici.objects.create_user(username=role, password="unused", rol=role)
    client.force_authenticate(user)
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        response = client.post(URL, payload(machine), format="json")
    assert response.status_code == 201
    assert response.data["tekrarlandi"] is False
    assert response.data["makine"]["kod"] == "M-1"
    assert "payload_fingerprint" not in response.data


def test_idempotent_repeat_returns_same_record_without_inference(client, user, machine):
    request = payload(machine)
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ) as inference:
        first = client.post(URL, request, format="json")
        second = client.post(URL, request, format="json")
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.data["id"] == second.data["id"]
    assert second.data["tekrarlandi"] is True
    assert inference.call_count == 1
    assert TahminKaydi.objects.count() == 1


def test_same_key_different_payload_is_safe_conflict(client, user, machine):
    first = payload(machine)
    changed = deepcopy(first)
    changed["sensor_verisi"]["tork_nm"] = 43
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        assert client.post(URL, first, format="json").status_code == 201
        response = client.post(URL, changed, format="json", HTTP_X_TRACE_ID="trace-409")
    assert response.status_code == 409
    assert response.data["hata"]["kod"] == "IDEMPOTENCY_CAKISMASI"
    assert response.data["hata"]["trace_id"] == "trace-409"
    assert "fingerprint" not in str(response.data).lower()


def test_low_risk_record_has_no_failure_shap_or_erp(client, user, machine):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(high=False),
    ):
        response = client.post(URL, payload(machine), format="json")
    assert response.status_code == 201
    assert response.data["ariza_tipleri"] == []
    assert response.data["shap_etkileri"] == []
    assert response.data["erp_snapshotlari"] == []


def test_high_risk_snapshots_shap_and_deterministic_erp_policy(client, user, machine):
    hdf_part = Parca.objects.create(parca_kodu="H-1", ad="Fan")
    twf_part = Parca.objects.create(parca_kodu="T-1", ad="Tool")
    Stok.objects.create(parca=hdf_part, adet=2, minimum_stok=1, tedarik_gun=3)
    ArizaParcaKurali.objects.create(
        ariza_tipi="HDF", parca=hdf_part, onerilen_aksiyon="Check", gerekli_miktar=3
    )
    ArizaParcaKurali.objects.create(
        ariza_tipi="TWF", parca=twf_part, onerilen_aksiyon="Inspect"
    )
    ArizaParcaKurali.objects.create(
        ariza_tipi="RNF", parca=None, onerilen_aksiyon="Ignore"
    )
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        response = client.post(URL, payload(machine), format="json")
    assert response.status_code == 201
    assert [item["kod"] for item in response.data["ariza_tipleri"]] == ["HDF", "TWF"]
    assert {item["ariza_tipi"] for item in response.data["erp_snapshotlari"]} == {
        "HDF",
        "TWF",
    }
    assert all(
        item["ariza_tipi"] != "RNF" for item in response.data["erp_snapshotlari"]
    )
    hdf = next(
        item
        for item in response.data["erp_snapshotlari"]
        if item["ariza_tipi"] == "HDF"
    )
    assert hdf["stok_yeterli"] is False
    assert (
        next(
            item
            for item in response.data["erp_snapshotlari"]
            if item["ariza_tipi"] == "TWF"
        )["deneysel"]
        is True
    )
    missing = next(
        item
        for item in response.data["erp_snapshotlari"]
        if item["ariza_tipi"] == "TWF"
    )
    assert missing["stok_durumu"] == "KAYIT_YOK"
    assert missing["toplam_stok"] is None
    assert missing["tedarik_gun"] is None
    assert missing["stok_yeterli"] is False


def test_zero_stock_and_missing_stock_are_distinct(client, user, machine):
    zero_part = Parca.objects.create(parca_kodu="ZERO", ad="Zero")
    missing_part = Parca.objects.create(parca_kodu="MISSING", ad="Missing")
    Stok.objects.create(parca=zero_part, adet=0, minimum_stok=2, tedarik_gun=4)
    for order, part in enumerate((zero_part, missing_part), start=1):
        ArizaParcaKurali.objects.create(
            ariza_tipi="HDF",
            parca=part,
            onerilen_aksiyon="Check",
            tercih_sirasi=order,
        )
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        response = client.post(URL, payload(machine), format="json")
    snapshots = {
        item["parca_kodu_snapshot"]: item for item in response.data["erp_snapshotlari"]
    }
    assert snapshots["ZERO"]["stok_durumu"] == "MEVCUT"
    assert snapshots["ZERO"]["toplam_stok"] == 0
    assert snapshots["ZERO"]["tedarik_gun"] == 4
    assert snapshots["MISSING"]["stok_durumu"] == "KAYIT_YOK"
    assert snapshots["MISSING"]["toplam_stok"] is None
    assert snapshots["MISSING"]["tedarik_gun"] is None
    assert snapshots["MISSING"]["stok_yeterli"] is False


def test_live_domain_changes_do_not_change_snapshots(client, user, machine):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(high=False),
    ):
        created = client.post(URL, payload(machine), format="json")
    machine.ad = "Changed"
    machine.kritiklik = 1
    machine.save()
    detail = client.get(f"{URL}{created.data['id']}/")
    assert detail.data["makine"]["ad"] == "CNC"
    assert detail.data["makine"]["kritiklik_snapshot"] == 5


def test_live_part_and_stock_changes_do_not_change_snapshots(client, user, machine):
    part = Parca.objects.create(parca_kodu="P-1", ad="Original")
    stock = Stok.objects.create(parca=part, adet=4, minimum_stok=2, tedarik_gun=6)
    ArizaParcaKurali.objects.create(
        ariza_tipi="HDF", parca=part, onerilen_aksiyon="Check"
    )
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        created = client.post(URL, payload(machine), format="json")
    part.ad = "Changed"
    part.save()
    stock.adet = 0
    stock.tedarik_gun = 99
    stock.save()
    detail = client.get(f"{URL}{created.data['id']}/")
    snapshot = detail.data["erp_snapshotlari"][0]
    assert snapshot["parca_adi_snapshot"] == "Original"
    assert snapshot["toplam_stok"] == 4
    assert snapshot["tedarik_gun"] == 6


def test_list_is_paginated_filtered_and_summary_only(client, user, machine):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(high=False),
    ):
        client.post(URL, payload(machine), format="json")
    response = client.get(URL, {"makine_id": machine.pk, "risk_uyarisi": "false"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert "shap_etkileri" not in response.data["results"][0]


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_prediction_records_are_not_mutable_over_api(client, user, machine, method):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(high=False),
    ):
        created = client.post(URL, payload(machine), format="json")
    assert (
        getattr(client, method)(
            f"{URL}{created.data['id']}/", {}, format="json"
        ).status_code
        == 405
    )


def test_validation_and_service_errors_do_not_write_records(client, user, machine):
    invalid = payload(machine)
    invalid["olcum_zamani"] = (timezone.now() + timedelta(minutes=6)).isoformat()
    assert client.post(URL, invalid, format="json").status_code == 400
    assert TahminKaydi.objects.count() == 0


def test_model_service_error_does_not_write_record(client, user, machine):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        side_effect=ModelHizmetiHatasi,
    ):
        response = client.post(URL, payload(machine), format="json")
    assert response.status_code == 503
    assert TahminKaydi.objects.count() == 0


def test_child_failure_rolls_back_entire_record(client, user, machine):
    with (
        patch(
            "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
            return_value=result(),
        ),
        patch(
            "apps.tahminler.record_services._ariza_ve_erp_kaydet",
            side_effect=RuntimeError("child failed"),
        ),
    ):
        response = client.post(URL, payload(machine), format="json")
    assert response.status_code == 500
    assert TahminKaydi.objects.count() == 0


def test_erp_failure_rolls_back_main_and_all_children(client, user, machine):
    part = Parca.objects.create(parca_kodu="P-ERP", ad="ERP")
    ArizaParcaKurali.objects.create(
        ariza_tipi="HDF", parca=part, onerilen_aksiyon="Check"
    )
    with (
        patch(
            "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
            return_value=result(),
        ),
        patch.object(ErpSnapshot.objects, "create", side_effect=RuntimeError("erp")),
    ):
        assert client.post(URL, payload(machine), format="json").status_code == 500
    assert TahminKaydi.objects.count() == 0
    assert ArizaTipiSnapshot.objects.count() == 0
    assert ShapEtkisiSnapshot.objects.count() == 0


def test_fingerprint_is_order_independent_and_float_deterministic(machine):
    now = timezone.now()
    first = payload_fingerprint(
        makine_id=machine.pk, olcum_zamani=now, kaynak="MANUEL", sensor_verisi=SENSOR
    )
    second = payload_fingerprint(
        makine_id=machine.pk,
        olcum_zamani=now,
        kaynak="MANUEL",
        sensor_verisi=dict(reversed(list(SENSOR.items()))),
    )
    assert first == second


def test_fingerprint_normalizes_timezone_equivalent_instants_and_negative_zero(machine):
    utc = datetime(2026, 8, 18, 12, 0, tzinfo=datetime_timezone.utc)
    plus_three = utc.astimezone(datetime_timezone(timedelta(hours=3)))
    negative_zero = {**SENSOR, "takim_asinmasi_dk": -0.0, "tork_nm": 42.80}
    positive_zero = {**SENSOR, "takim_asinmasi_dk": 0.0, "tork_nm": 42.8}
    first = payload_fingerprint(
        makine_id=machine.pk,
        olcum_zamani=utc,
        kaynak="MANUEL",
        sensor_verisi=negative_zero,
    )
    second = payload_fingerprint(
        makine_id=machine.pk,
        olcum_zamani=plus_three,
        kaynak="MANUEL",
        sensor_verisi=positive_zero,
    )
    later = payload_fingerprint(
        makine_id=machine.pk,
        olcum_zamani=utc + timedelta(seconds=1),
        kaynak="MANUEL",
        sensor_verisi=positive_zero,
    )
    assert first == second
    assert first != later


def test_database_uniqueness_constraints(user, machine):
    values = record_values(user, machine)
    record = TahminKaydi.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        TahminKaydi.objects.create(**values)
    ArizaTipiSnapshot.objects.create(
        tahmin=record,
        kod="HDF",
        olasilik=0.5,
        threshold=0.4,
        esik_asildi=True,
        operasyonel_kullanima_uygun=True,
        guvenilir_aday=True,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ArizaTipiSnapshot.objects.create(
            tahmin=record,
            kod="HDF",
            olasilik=0.5,
            threshold=0.4,
            esik_asildi=True,
            operasyonel_kullanima_uygun=True,
            guvenilir_aday=True,
        )
    assert TahminKaydi.objects.create(
        **record_values(user, machine, idempotency_key="after-error")
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("risk_orani", -0.1),
        ("risk_orani", 1.1),
        ("binary_threshold", -0.1),
        ("binary_threshold", 1.1),
    ),
)
def test_risk_and_threshold_database_constraints(user, machine, field, value):
    with pytest.raises(IntegrityError), transaction.atomic():
        TahminKaydi.objects.create(**record_values(user, machine, **{field: value}))


def test_shap_order_is_unique_per_target(user, machine):
    record = TahminKaydi.objects.create(**record_values(user, machine))
    values = dict(
        tahmin=record,
        hedef="machine_failure",
        sira=1,
        feature="tork_nm",
        gorunen_ad="Tork",
        original_feature_value=42.8,
        model_feature_value=42.8,
        shap_value=0.2,
        yon="ARTIRIR",
    )
    ShapEtkisiSnapshot.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        ShapEtkisiSnapshot.objects.create(**values)


def test_snapshot_instance_and_queryset_mutation_are_blocked(user, machine):
    record = TahminKaydi.objects.create(**record_values(user, machine))
    record.risk_orani = 0.9
    with pytest.raises(ValueError):
        record.save()
    with pytest.raises(ValueError):
        record.delete()
    with pytest.raises(ValueError):
        TahminKaydi.objects.filter(pk=record.pk).update(risk_orani=0.9)
    with pytest.raises(ValueError):
        TahminKaydi.objects.filter(pk=record.pk).delete()


def test_machine_and_user_deletion_are_protected(user, machine):
    TahminKaydi.objects.create(**record_values(user, machine))
    with pytest.raises(ProtectedError):
        machine.delete()
    with pytest.raises(ProtectedError):
        user.delete()


def test_persistent_flow_prepares_features_once_without_mutating_input(
    client, user, machine
):
    request = payload(machine)
    original = deepcopy(request)
    with (
        patch(
            "apps.tahminler.record_services._ozellikleri_hazirla",
            wraps=_ozellikleri_hazirla,
        ) as prepare,
        patch(
            "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
            return_value=result(high=False),
        ) as inference,
    ):
        assert client.post(URL, request, format="json").status_code == 201
    assert prepare.call_count == 1
    assert "features" in inference.call_args.kwargs
    assert request == original


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_requests_create_one_postgresql_record():
    if connection.vendor != "postgresql":
        pytest.skip("Concurrency contract is PostgreSQL-specific.")
    user = Kullanici.objects.create_user(username="concurrent", password="unused")
    machine = Makine.objects.create(
        makine_kodu="M-CONCURRENT", ad="Concurrent", tip="Test", kritiklik=3
    )
    request = payload(machine, key="concurrent-reading")
    barrier = Barrier(2)

    def synchronized_inference(*args, **kwargs):
        barrier.wait(timeout=10)
        return result(high=False)

    def send_request(_):
        close_old_connections()
        thread_client = APIClient()
        thread_client.force_authenticate(user)
        response = thread_client.post(URL, request, format="json")
        close_old_connections()
        return response.status_code, response.data["id"]

    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        side_effect=synchronized_inference,
    ) as inference:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(send_request, range(2)))

    assert sorted(status for status, _ in responses) == [200, 201]
    assert len({record_id for _, record_id in responses}) == 1
    assert inference.call_count == 2
    assert (
        TahminKaydi.objects.filter(
            makine=machine, idempotency_key="concurrent-reading"
        ).count()
        == 1
    )


def test_stateless_endpoint_does_not_create_record(client, user):
    with patch(
        "apps.tahminler.services.hiyerarsik_risk_tahmini_yap",
        return_value=result(high=False),
    ):
        assert (
            client.post("/api/tahminler/risk/", SENSOR, format="json").status_code
            == 200
        )
    assert TahminKaydi.objects.count() == 0


def test_list_and_detail_have_bounded_query_counts(
    client, user, machine, django_assert_max_num_queries
):
    with patch(
        "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
        return_value=result(),
    ):
        created = client.post(URL, payload(machine), format="json")
    with django_assert_max_num_queries(6):
        assert client.get(URL).status_code == 200
    with django_assert_max_num_queries(7):
        assert client.get(f"{URL}{created.data['id']}/").status_code == 200
