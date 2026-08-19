from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier, Event
from unittest.mock import patch

import pandas as pd
import pytest
from django.db import close_old_connections, connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bakim.models import BakimIsEmri, IsEmriOlayi, Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import ReplayCakismasiHatasi
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    BakimKarariSnapshot,
    ReplayOgesi,
    ReplayOlayi,
    ReplayOturumu,
    TahminKaydi,
)
from apps.tahminler.replay_policy import (
    GROUND_TRUTH_FIELDS,
    SENSOR_FIELDS,
    TRANSITIONS,
    ReplayPolitikaHatasi,
    gecisi_dogrula,
    replay_metrics,
    snapshots_from_row,
)
from apps.tahminler.replay_services import _claim, _finalize_success

pytestmark = pytest.mark.django_db
URL = "/api/tahminler/replay-oturumlari/"


@pytest.fixture
def admin():
    return Kullanici.objects.create_user(username="replay-admin", rol="ADMIN")


@pytest.fixture
def user():
    return Kullanici.objects.create_user(username="replay-user", rol="USER")


@pytest.fixture
def machine():
    return Makine.objects.create(
        makine_kodu="RP-M1", ad="Replay", tip="Test", kritiklik=4
    )


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def frame(count=3):
    rows = []
    for index in range(count):
        rows.append(
            {
                "urun_tipi": "L",
                "hava_sicakligi_k": 298.1,
                "proses_sicakligi_k": 308.6,
                "donus_hizi_rpm": 1551.0,
                "tork_nm": 42.8,
                "takim_asinmasi_dk": float(index),
                "makine_arizasi": int(index == 1),
                "TWF": 0,
                "HDF": int(index == 1),
                "PWF": 0,
                "OSF": 0,
                "RNF": 0,
                "machine_id": f"M-{index + 1:03d}",
                "_timestamp": pd.Timestamp("2020-01-01", tz="UTC")
                + timedelta(minutes=index),
                "_source_index": 100 + index,
            }
        )
    return pd.DataFrame(rows)


def create_body(machine, count=3):
    return {
        "split": "test",
        "baslangic_ofseti": 0,
        "kayit_sayisi": count,
        "varsayilan_batch_boyutu": 2,
        "sanal_aralik_saniye": 60,
        "makine_id": machine.pk,
    }


def create_session(admin, machine, count=3):
    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(count), "a" * 64),
    ):
        response = client_for(admin).post(
            URL, create_body(machine, count), format="json"
        )
    assert response.status_code == 201
    return response


def prediction(actor, machine, key="replay-prediction", source="REPLAY"):
    record = TahminKaydi.objects.create(
        makine=machine,
        olusturan=actor,
        trace_id="t",
        kaynak=source,
        olcum_zamani=timezone.now(),
        idempotency_key=key,
        payload_fingerprint="a" * 64,
        makine_kodu_snapshot=machine.makine_kodu,
        makine_adi_snapshot=machine.ad,
        kritiklik_snapshot=4,
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
        tedarik_riski_skoru=0,
        nihai_oncelik_skoru=64,
        oncelik_seviyesi="YUKSEK",
        ana_aksiyon="ONCELIKLI_BAKIM_PLANLA",
        karar_guveni="ORTA",
    )
    return record


def test_sensor_and_truth_are_separate_and_input_is_immutable():
    row = frame(1).iloc[0].to_dict()
    original = deepcopy(row)
    sensor, truth = snapshots_from_row(row)
    assert tuple(sensor) == SENSOR_FIELDS
    assert tuple(truth) == GROUND_TRUTH_FIELDS
    assert not set(sensor).intersection(GROUND_TRUTH_FIELDS)
    assert row == original


@pytest.mark.parametrize(
    ("source", "target"),
    (
        ("HAZIR", "CALISIYOR"),
        ("CALISIYOR", "DURAKLATILDI"),
        ("DURAKLATILDI", "CALISIYOR"),
        ("HATALI", "CALISIYOR"),
        ("CALISIYOR", "TAMAMLANDI"),
        ("HAZIR", "IPTAL_EDILDI"),
    ),
)
def test_replay_state_machine_allowed(source, target):
    assert gecisi_dogrula(source, target) is None


def test_same_and_terminal_transitions_are_rejected():
    for source, target in (
        ("HAZIR", "HAZIR"),
        ("TAMAMLANDI", "CALISIYOR"),
        ("IPTAL_EDILDI", "CALISIYOR"),
    ):
        with pytest.raises(ReplayPolitikaHatasi):
            gecisi_dogrula(source, target)


def test_binary_and_label_metrics_are_deterministic_and_safe():
    records = [
        {
            "truth": {
                "makine_arizasi": 1,
                "HDF": 1,
                "PWF": 0,
                "OSF": 0,
                "TWF": 0,
                "RNF": 0,
            },
            "risk_orani": 0.9,
            "binary_threshold": 0.5,
            "predicted_labels": {"HDF"},
        },
        {
            "truth": {
                "makine_arizasi": 0,
                "HDF": 0,
                "PWF": 0,
                "OSF": 0,
                "TWF": 1,
                "RNF": 1,
            },
            "risk_orani": 0.8,
            "binary_threshold": 0.5,
            "predicted_labels": {"TWF"},
        },
    ]
    original = deepcopy(records)
    result = replay_metrics(records)
    assert tuple(
        result["binary"]["confusion_matrix"][key]
        for key in (
            "true_negative",
            "false_positive",
            "false_negative",
            "true_positive",
        )
    ) == (
        0,
        1,
        0,
        1,
    )
    assert result["failure_types"]["TWF"]["politika"] == "DENEYSEL"
    assert result["rnf_ground_truth_count"] == 1
    assert records == original
    assert replay_metrics([])["binary"] is None


def test_create_is_deterministic_bounded_and_has_no_leakage(admin, machine):
    response = create_session(admin, machine)
    session = ReplayOturumu.objects.get(pk=response.data["id"])
    items = list(session.ogeler.all())
    assert [x.sira for x in items] == [1, 2, 3]
    assert [x.kaynak_satir_kimligi for x in items] == [100, 101, 102]
    assert set(items[0].sensor_snapshot) == set(SENSOR_FIELDS)
    assert set(items[0].ground_truth_snapshot) == set(GROUND_TRUTH_FIELDS)
    assert session.olaylar.get().olay_tipi == "OTURUM_OLUSTURULDU"


def test_idempotent_public_creation_reuses_same_real_session(admin, machine):
    from apps.tahminler.replay_services import (
        replay_butunlugunu_dogrula,
        replay_olustur,
    )

    data = create_body(machine, 3)
    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(3), "a" * 64),
    ):
        first = replay_olustur(
            actor=admin, trace_id="seed-1", data=data, idempotent=True
        )
        second = replay_olustur(
            actor=admin, trace_id="seed-2", data=data, idempotent=True
        )

    assert first.pk == second.pk
    assert ReplayOturumu.objects.count() == 1
    assert replay_butunlugunu_dogrula(first) == first.toplam_oge == 3
    assert first.durum == ReplayOturumu.Durum.HAZIR
    assert first.ogeler.filter(tahmin_kaydi__isnull=False).count() == 0


def test_admin_mutations_user_read_and_auth(admin, user, machine):
    created = create_session(admin, machine, 1)
    endpoint = f"{URL}{created.data['id']}/baslat/"
    assert client_for(user).get(URL).status_code == 200
    assert (
        client_for(user)
        .post(endpoint, {"beklenen_version": 1}, format="json")
        .status_code
        == 403
    )
    started = client_for(admin).post(endpoint, {"beklenen_version": 1}, format="json")
    stale = client_for(admin).post(endpoint, {"beklenen_version": 1}, format="json")
    assert started.status_code == 200 and started.data["durum"] == "CALISIYOR"
    assert stale.status_code == 409
    assert started.data["version"] == 2
    assert started.data["baslatilma_zamani"] is not None
    assert stale.data["hata"]["trace_id"] == stale["X-Trace-ID"]
    assert APIClient().get(URL).status_code == 401


def test_pause_blocks_step_and_resume(admin, machine):
    created = create_session(admin, machine)
    client = client_for(admin)
    pk = created.data["id"]
    client.post(f"{URL}{pk}/baslat/", {"beklenen_version": 1}, format="json")
    paused = client.post(f"{URL}{pk}/duraklat/", {"beklenen_version": 2}, format="json")
    blocked = client.post(f"{URL}{pk}/adim/", {"beklenen_version": 3}, format="json")
    resumed = client.post(
        f"{URL}{pk}/devam-et/", {"beklenen_version": 3}, format="json"
    )
    assert paused.status_code == 200 and blocked.status_code == 409
    assert resumed.status_code == 200


def test_step_uses_only_sensor_snapshot_and_completes(admin, machine):
    created = create_session(admin, machine, 1)
    client = client_for(admin)
    pk = created.data["id"]
    client.post(f"{URL}{pk}/baslat/", {"beklenen_version": 1}, format="json")
    made = prediction(admin, machine)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs["veriler"]["sensor_verisi"])
        return made, False

    with patch(
        "apps.tahminler.replay_services.tahmin_kaydi_olustur", side_effect=fake_create
    ):
        response = client.post(
            f"{URL}{pk}/adim/",
            {"beklenen_version": 2, "batch_boyutu": 1},
            format="json",
        )
    assert response.status_code == 200 and response.data["durum"] == "TAMAMLANDI"
    item = ReplayOgesi.objects.get(oturum_id=pk)
    assert item.durum == "BASARILI" and item.tahmin_kaydi == made
    assert set(captured) == set(SENSOR_FIELDS)
    assert BakimIsEmri.objects.filter(tahmin_kaydi=made).count() == 0


def test_item_failure_does_not_rollback_other_items(admin, machine):
    created = create_session(admin, machine, 2)
    client = client_for(admin)
    pk = created.data["id"]
    client.post(f"{URL}{pk}/baslat/", {"beklenen_version": 1}, format="json")
    made = prediction(admin, machine)
    with patch(
        "apps.tahminler.replay_services.tahmin_kaydi_olustur",
        side_effect=[RuntimeError("internal"), (made, False)],
    ):
        response = client.post(
            f"{URL}{pk}/adim/",
            {"beklenen_version": 2, "batch_boyutu": 2},
            format="json",
        )
    assert response.status_code == 200
    assert list(
        ReplayOgesi.objects.filter(oturum_id=pk).values_list("durum", flat=True)
    ) == ["BASARISIZ", "BASARILI"]
    session = ReplayOturumu.objects.get(pk=pk)
    event = session.olaylar.get(olay_tipi="OGELER_ISLENDI")
    assert session.durum == "TAMAMLANDI" and session.version == 3
    assert (event.basarili_sayisi, event.basarisiz_sayisi) == (1, 1)


def test_active_claim_rejects_concurrent_step(admin, machine):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.durum, session.version, session.adim_aktif = "CALISIYOR", 2, True
    session.save()
    item = session.ogeler.get()
    item.durum = "ISLENIYOR"
    item.islem_baslangic_zamani = timezone.now()
    item.save()
    response = client_for(admin).post(
        f"{URL}{session.pk}/adim/", {"beklenen_version": 2}, format="json"
    )
    assert response.status_code == 409
    assert response.data["hata"]["kod"] == "REPLAY_ADIMI_ZATEN_CALISIYOR"


def test_stale_claim_is_recovered(admin, machine):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.durum, session.version, session.adim_aktif = "CALISIYOR", 2, True
    session.save()
    item = session.ogeler.get()
    item.durum, item.islem_baslangic_zamani = (
        "ISLENIYOR",
        timezone.now() - timedelta(minutes=11),
    )
    item.save()
    made = prediction(admin, machine)
    with patch(
        "apps.tahminler.replay_services.tahmin_kaydi_olustur",
        return_value=(made, False),
    ):
        response = client_for(admin).post(
            f"{URL}{session.pk}/adim/", {"beklenen_version": 2}, format="json"
        )
    assert response.status_code == 200
    item.refresh_from_db()
    assert item.deneme_sayisi == 1 and item.durum == "BASARILI"


def test_replay_prediction_cannot_create_work_order(admin, machine):
    made = prediction(admin, machine)
    response = client_for(admin).post(
        "/api/bakim/is-emirleri/",
        {
            "tahmin_kaydi_id": str(made.pk),
            "idempotency_key": "replay-wo",
            "baslik": "Replay",
            "aciklama": "Yasak",
        },
        format="json",
    )
    assert response.status_code == 409
    assert response.data["hata"]["kod"] == "REPLAY_TAHMININDEN_IS_EMRI_OLUSTURULAMAZ"


def test_filters_items_unknown_and_405(admin, machine):
    created = create_session(admin, machine)
    client = client_for(admin)
    pk = created.data["id"]
    listing = client.get(URL, {"durum": "HAZIR", "sirala": "toplam_oge"})
    assert listing.data["count"] == 1
    assert set(("count", "next", "previous", "results")) <= set(listing.data)
    assert (
        client.get(f"{URL}{pk}/ogeler/", {"ground_truth_binary": "true"}).status_code
        == 200
    )
    assert client.get(URL, {"unknown": "x"}).status_code == 400
    for method in (client.put, client.patch, client.delete):
        assert method(f"{URL}{pk}/", {}, format="json").status_code == 405


def test_replay_query_counts_are_bounded(admin, machine, django_assert_max_num_queries):
    created = create_session(admin, machine)
    client = client_for(admin)
    pk = created.data["id"]
    with django_assert_max_num_queries(3):
        assert client.get(URL).status_code == 200
    with django_assert_max_num_queries(4):
        assert client.get(f"{URL}{pk}/").status_code == 200
    with django_assert_max_num_queries(5):
        assert client.get(f"{URL}{pk}/ogeler/").status_code == 200


def _concurrent_claim(barrier, session_id, actor_id):
    close_old_connections()
    try:
        actor = Kullanici.objects.get(pk=actor_id)
        barrier.wait()
        session, items, _ = _claim(
            session_id=session_id,
            actor=actor,
            trace_id="concurrent",
            expected_version=2,
            batch_size=1,
            now=timezone.now(),
        )
        return "ok", session.version, [item.pk for item in items]
    except ReplayCakismasiHatasi as exc:
        return "conflict", exc.kod, []
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_steps_only_one_claims_item(admin, machine):
    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(2), "a" * 64),
    ):
        from apps.tahminler.replay_services import replay_gecis, replay_olustur

        session = replay_olustur(
            actor=admin, trace_id="t", data=create_body(machine, 2)
        )
        replay_gecis(
            session_id=session.pk,
            actor=admin,
            trace_id="t",
            expected_version=1,
            target="CALISIYOR",
        )
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _concurrent_claim(barrier, session.pk, admin.pk), range(2)
            )
        )
    assert sorted(item[0] for item in results) == ["conflict", "ok"]
    claimed_ids = [pk for result in results for pk in result[2]]
    assert len(claimed_ids) == len(set(claimed_ids)) == 1


def test_all_disallowed_state_transitions_are_rejected():
    states = tuple(TRANSITIONS)
    for source in states:
        for target in states:
            if target not in TRANSITIONS[source]:
                with pytest.raises(ReplayPolitikaHatasi):
                    gecisi_dogrula(source, target)


def test_create_validation_bounds_unknown_body_and_inactive_machine(admin, machine):
    client = client_for(admin)
    body = create_body(machine)
    body["kayit_sayisi"] = 1001
    assert client.post(URL, body, format="json").status_code == 400
    body = create_body(machine)
    body["varsayilan_batch_boyutu"] = 26
    assert client.post(URL, body, format="json").status_code == 400
    body = create_body(machine)
    body["bilinmeyen"] = True
    assert client.post(URL, body, format="json").status_code == 400
    machine.aktif = False
    machine.save()
    assert client.post(URL, create_body(machine), format="json").status_code == 400


@pytest.mark.parametrize(
    "error", (OSError("missing"), ValueError("broken"), KeyError("sha"))
)
def test_session_fatal_metadata_errors_leave_no_partial_rows(admin, machine, error):
    metadata_path = type(
        "BrokenMetadataPath",
        (),
        {"read_text": lambda *args, **kwargs: (_ for _ in ()).throw(error)},
    )()
    with patch(
        "apps.tahminler.replay_services.settings.REPLAY_PREPARED_METADATA_PATH",
        metadata_path,
    ):
        response = client_for(admin).post(URL, create_body(machine), format="json")
    assert response.status_code == 503
    assert response.data["hata"]["kod"] == "REPLAY_VERI_SETI_KULLANILAMIYOR"
    rendered = str(response.data)
    assert "missing" not in rendered and "broken" not in rendered
    assert ReplayOturumu.objects.count() == ReplayOgesi.objects.count() == 0


def test_session_fatal_checksum_or_dataset_contract_leaves_no_partial_rows(
    admin, machine
):
    from bakim_ml.loaders import DatasetLoadError

    for error in (DatasetLoadError("checksum/path"), KeyError("timestamp")):
        with patch(
            "apps.tahminler.replay_services.load_prepared_dataset",
            side_effect=error,
        ):
            response = client_for(admin).post(URL, create_body(machine), format="json")
        assert response.status_code == 503
        assert "checksum/path" not in str(response.data)
        assert ReplayOturumu.objects.count() == ReplayOgesi.objects.count() == 0


def test_child_bulk_create_failure_rolls_back_session_and_event(admin, machine):
    with (
        patch(
            "apps.tahminler.replay_services._load_selected",
            return_value=(frame(2), "a" * 64),
        ),
        patch.object(ReplayOgesi.objects, "bulk_create", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        from apps.tahminler.replay_services import replay_olustur

        replay_olustur(actor=admin, trace_id="t", data=create_body(machine, 2))
    assert ReplayOturumu.objects.count() == 0
    assert ReplayOgesi.objects.count() == 0
    assert ReplayOlayi.objects.count() == 0


def test_default_and_max_batch_claim_deterministic_order(admin, machine):
    created = create_session(admin, machine, 30)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.durum, session.version = "CALISIYOR", 2
    session.save()
    _, default_items, _ = _claim(
        session_id=session.pk,
        actor=admin,
        trace_id="batch",
        expected_version=2,
        batch_size=5,
        now=timezone.now(),
    )
    assert [item.sira for item in default_items] == [1, 2, 3, 4, 5]
    session.adim_aktif, session.aktif_claim_token = False, None
    session.version = 3
    session.save()
    ReplayOgesi.objects.filter(pk__in=[x.pk for x in default_items]).update(
        durum="BASARILI", processing_token=None
    )
    _, max_items, _ = _claim(
        session_id=session.pk,
        actor=admin,
        trace_id="batch",
        expected_version=3,
        batch_size=25,
        now=timezone.now(),
    )
    assert [item.sira for item in max_items] == list(range(6, 31))


def test_inference_runs_outside_atomic_and_uses_exact_replay_contract(admin, machine):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.durum, session.version = "CALISIYOR", 2
    session.save()
    made = prediction(admin, machine)
    captured = {}
    outer_atomic_depth = len(connection.atomic_blocks)

    def fake_create(**kwargs):
        captured.update(kwargs["veriler"])
        captured["atomic_depth"] = len(connection.atomic_blocks)
        return made, False

    with patch(
        "apps.tahminler.replay_services.tahmin_kaydi_olustur", side_effect=fake_create
    ):
        from apps.tahminler.replay_services import replay_adim

        replay_adim(
            session_id=session.pk,
            actor=admin,
            trace_id="trace",
            expected_version=2,
            batch_size=1,
        )
    item = ReplayOgesi.objects.get(oturum=session)
    assert captured["idempotency_key"] == f"replay:{session.pk}:1"
    assert captured["kaynak"] == "REPLAY"
    assert captured["olcum_zamani"] == item.sanal_timestamp
    assert captured["atomic_depth"] == outer_atomic_depth
    assert item.tamamlanma_zamani >= item.islem_baslangic_zamani


def test_token_ownership_rejects_wrong_and_second_finalization(admin, machine):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.durum, session.version = "CALISIYOR", 2
    session.save()
    _, items, token = _claim(
        session_id=session.pk,
        actor=admin,
        trace_id="token",
        expected_version=2,
        batch_size=1,
        now=timezone.now(),
    )
    made = prediction(admin, machine)
    import time
    import uuid

    assert not _finalize_success(
        item_id=items[0].pk,
        token=uuid.uuid4(),
        prediction=made,
        trace_id="wrong",
        started=time.perf_counter(),
    )
    assert _finalize_success(
        item_id=items[0].pk,
        token=token,
        prediction=made,
        trace_id="right",
        started=time.perf_counter(),
    )
    assert not _finalize_success(
        item_id=items[0].pk,
        token=token,
        prediction=made,
        trace_id="second",
        started=time.perf_counter(),
    )
    item = ReplayOgesi.objects.get(pk=items[0].pk)
    assert item.tahmin_kaydi == made and item.trace_id == "right"


def test_stale_claim_boundary_attempt_limit_and_retry_selection(admin, machine):
    created = create_session(admin, machine, 3)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    now = timezone.now()
    session.durum, session.version, session.adim_aktif = "CALISIYOR", 2, True
    session.save()
    first, second, third = list(session.ogeler.all())
    first.durum, first.islem_baslangic_zamani = (
        "ISLENIYOR",
        now - timedelta(seconds=599),
    )
    first.save()
    with pytest.raises(ReplayCakismasiHatasi):
        _claim(
            session_id=session.pk,
            actor=admin,
            trace_id="before",
            expected_version=2,
            batch_size=1,
            now=now,
        )
    first.islem_baslangic_zamani = now - timedelta(seconds=600)
    first.save()
    _, claimed, _ = _claim(
        session_id=session.pk,
        actor=admin,
        trace_id="boundary",
        expected_version=2,
        batch_size=1,
        now=now,
    )
    assert claimed[0].pk == first.pk and claimed[0].deneme_sayisi == 1
    ReplayOgesi.objects.filter(pk=first.pk).update(durum="BASARISIZ", deneme_sayisi=3)
    ReplayOgesi.objects.filter(pk=second.pk).update(durum="BASARISIZ", deneme_sayisi=2)
    ReplayOgesi.objects.filter(pk=third.pk).update(durum="BASARILI")
    session.adim_aktif, session.aktif_claim_token, session.version = False, None, 4
    session.save()
    from apps.tahminler.replay_services import basarisizlari_yeniden_dene

    _, count = basarisizlari_yeniden_dene(
        session_id=session.pk,
        actor=admin,
        trace_id="retry",
        expected_version=4,
    )
    assert count == 1
    assert ReplayOgesi.objects.get(pk=first.pk).durum == "BASARISIZ"
    assert ReplayOgesi.objects.get(pk=second.pk).durum == "BEKLIYOR"
    assert ReplayOgesi.objects.get(pk=third.pk).durum == "BASARILI"


@pytest.mark.django_db(transaction=True)
def test_stale_recovery_new_token_fences_old_finalization(admin, machine):
    import time
    import uuid

    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    old_token = uuid.uuid4()
    session.durum, session.version = "CALISIYOR", 2
    session.adim_aktif, session.aktif_claim_token = True, old_token
    session.save()
    item = session.ogeler.get()
    item.durum, item.processing_token = "ISLENIYOR", old_token
    item.islem_baslangic_zamani = timezone.now() - timedelta(seconds=600)
    item.deneme_sayisi = 1
    item.save()
    made = prediction(admin, machine)
    recovered = Event()

    def old_worker():
        close_old_connections()
        try:
            recovered.wait()
            old_prediction = TahminKaydi.objects.get(pk=made.pk)
            return _finalize_success(
                item_id=item.pk,
                token=old_token,
                prediction=old_prediction,
                trace_id="old",
                started=time.perf_counter(),
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as pool:
        old_result = pool.submit(old_worker)
        _, claimed, new_token = _claim(
            session_id=session.pk,
            actor=admin,
            trace_id="recovered",
            expected_version=2,
            batch_size=1,
            now=timezone.now(),
        )
        recovered.set()
        assert not old_result.result()
    assert new_token != old_token and claimed[0].deneme_sayisi == 2
    assert _finalize_success(
        item_id=item.pk,
        token=new_token,
        prediction=made,
        trace_id="new",
        started=time.perf_counter(),
    )
    item.refresh_from_db()
    assert item.durum == "BASARILI" and item.deneme_sayisi == 2


def test_metric_predicted_positive_policy_and_positive_values():
    record = {
        "truth": {
            "makine_arizasi": 1,
            "HDF": 1,
            "PWF": 0,
            "OSF": 0,
            "TWF": 1,
            "RNF": 1,
        },
        "risk_orani": 0.9,
        "binary_threshold": 0.5,
        "predicted_labels": {"HDF", "TWF"},
    }
    result = replay_metrics([record])
    assert result["binary"] == {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "support": 1,
        "predicted_positive": 1,
        "confusion_matrix": {
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 0,
            "true_positive": 1,
        },
        "pr_auc": 1.0,
    }
    assert result["failure_types"]["HDF"]["tp"] == 1
    assert result["failure_types"]["TWF"]["tp"] == 1
    assert "RNF" not in result["failure_types"]


def _attach_successful_items(session, actor, machine, count):
    items = list(session.ogeler.order_by("sira")[:count])
    for item in items:
        made = prediction(actor, machine, key=f"query-{session.pk}-{item.sira}")
        ArizaTipiSnapshot.objects.create(
            tahmin=made,
            kod="HDF",
            olasilik=0.8,
            threshold=0.5,
            esik_asildi=True,
            operasyonel_kullanima_uygun=True,
            guvenilir_aday=True,
            siralama=1,
        )
        item.durum, item.tahmin_kaydi = "BASARILI", made
        item.save()


def test_successful_item_list_query_count_is_constant_for_one_and_ten(admin, machine):
    one = create_session(admin, machine, 1)
    ten = create_session(admin, machine, 10)
    one_session = ReplayOturumu.objects.get(pk=one.data["id"])
    ten_session = ReplayOturumu.objects.get(pk=ten.data["id"])
    _attach_successful_items(one_session, admin, machine, 1)
    _attach_successful_items(ten_session, admin, machine, 10)
    client = client_for(admin)
    with CaptureQueriesContext(connection) as one_queries:
        assert client.get(f"{URL}{one_session.pk}/ogeler/").status_code == 200
    with CaptureQueriesContext(connection) as ten_queries:
        response = client.get(f"{URL}{ten_session.pk}/ogeler/")
    assert response.status_code == 200 and len(response.data["results"]) == 10
    assert len(one_queries) == len(ten_queries) == 6


def test_list_detail_item_and_metrics_query_bounds_with_success_relations(
    admin, machine
):
    created = create_session(admin, machine, 10)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    _attach_successful_items(session, admin, machine, 10)
    session.durum = ReplayOturumu.Durum.TAMAMLANDI
    session.save(update_fields=("durum",))
    client = client_for(admin)
    with CaptureQueriesContext(connection) as list_queries:
        assert client.get(URL).status_code == 200
    with CaptureQueriesContext(connection) as detail_queries:
        response = client.get(f"{URL}{session.pk}/")
    with CaptureQueriesContext(connection) as item_queries:
        assert client.get(f"{URL}{session.pk}/ogeler/").status_code == 200
    assert response.data["metrikler"]["degerlendirilen_oge_sayisi"] == 10
    assert (len(list_queries), len(detail_queries), len(item_queries)) == (2, 4, 6)


def _concurrent_transition(barrier, session_id, actor_id):
    close_old_connections()
    try:
        from apps.tahminler.replay_services import replay_gecis

        actor = Kullanici.objects.get(pk=actor_id)
        barrier.wait()
        session = replay_gecis(
            session_id=session_id,
            actor=actor,
            trace_id="start-race",
            expected_version=1,
            target="CALISIYOR",
        )
        return "ok", session.version
    except ReplayCakismasiHatasi as exc:
        return "conflict", exc.kod
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_version_start_has_one_event_and_version(admin, machine):
    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(1), "a" * 64),
    ):
        from apps.tahminler.replay_services import replay_olustur

        session = replay_olustur(
            actor=admin, trace_id="create", data=create_body(machine, 1)
        )
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _concurrent_transition(barrier, session.pk, admin.pk),
                range(2),
            )
        )
    session.refresh_from_db()
    assert sorted(result[0] for result in results) == ["conflict", "ok"]
    assert session.version == 2 and session.durum == "CALISIYOR"
    assert session.olaylar.filter(olay_tipi="BASLATILDI").count() == 1


def _concurrent_finalize(barrier, item_id, token, prediction_id):
    close_old_connections()
    try:
        import time

        prediction_record = TahminKaydi.objects.get(pk=prediction_id)
        barrier.wait()
        return _finalize_success(
            item_id=item_id,
            token=token,
            prediction=prediction_record,
            trace_id=str(token),
            started=time.perf_counter(),
        )
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_finalization_only_claim_token_writes(admin, machine):
    import uuid

    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(1), "a" * 64),
    ):
        from apps.tahminler.replay_services import replay_olustur

        session = replay_olustur(
            actor=admin, trace_id="create", data=create_body(machine, 1)
        )
    session.durum, session.version = "CALISIYOR", 2
    session.save()
    _, items, token = _claim(
        session_id=session.pk,
        actor=admin,
        trace_id="claim",
        expected_version=2,
        batch_size=1,
        now=timezone.now(),
    )
    made = prediction(admin, machine)
    wrong = uuid.uuid4()
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_concurrent_finalize, barrier, items[0].pk, value, made.pk)
            for value in (token, wrong)
        ]
        results = [future.result() for future in futures]
    item = ReplayOgesi.objects.get(pk=items[0].pk)
    assert sorted(results) == [False, True]
    assert item.durum == "BASARILI" and item.tahmin_kaydi_id == made.pk
    assert TahminKaydi.objects.filter(pk=made.pk).count() == 1


def _concurrent_retry(barrier, session_id, actor_id, expected_version):
    close_old_connections()
    try:
        from apps.tahminler.replay_services import basarisizlari_yeniden_dene

        actor = Kullanici.objects.get(pk=actor_id)
        barrier.wait()
        session, count = basarisizlari_yeniden_dene(
            session_id=session_id,
            actor=actor,
            trace_id="retry-race",
            expected_version=expected_version,
        )
        return "ok", count, session.version
    except ReplayCakismasiHatasi as exc:
        return "conflict", exc.kod, None
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_retry_only_enqueues_failed_item_once(admin, machine):
    with patch(
        "apps.tahminler.replay_services._load_selected",
        return_value=(frame(1), "a" * 64),
    ):
        from apps.tahminler.replay_services import replay_olustur

        session = replay_olustur(
            actor=admin, trace_id="create", data=create_body(machine, 1)
        )
    session.durum, session.version = "TAMAMLANDI", 2
    session.save()
    item = session.ogeler.get()
    item.durum, item.deneme_sayisi = "BASARISIZ", 1
    item.save()
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _concurrent_retry(barrier, session.pk, admin.pk, 2),
                range(2),
            )
        )
    session.refresh_from_db()
    item.refresh_from_db()
    assert sorted(result[0] for result in results) == ["conflict", "ok"]
    assert sum(result[1] == 1 for result in results) == 1
    assert session.version == 3 and item.durum == "BEKLIYOR"
    assert (
        session.olaylar.filter(olay_tipi="BASARISIZLAR_YENIDEN_HAZIRLANDI").count() == 1
    )


@pytest.mark.parametrize("source", ("MANUEL", "ENTEGRASYON"))
def test_non_replay_predictions_keep_work_order_flow(admin, machine, source):
    made = prediction(admin, machine, key=f"normal-{source}", source=source)
    response = client_for(admin).post(
        "/api/bakim/is-emirleri/",
        {
            "tahmin_kaydi_id": str(made.pk),
            "idempotency_key": f"work-{source}",
            "baslik": source,
            "aciklama": "Normal akış",
        },
        format="json",
    )
    assert response.status_code == 201
    assert BakimIsEmri.objects.filter(tahmin_kaydi=made).count() == 1
    assert IsEmriOlayi.objects.filter(is_emri__tahmin_kaydi=made).count() == 1


def test_replay_work_order_rejection_has_no_partial_rows_and_trace_matches(
    admin, machine
):
    made = prediction(admin, machine)
    response = client_for(admin).post(
        "/api/bakim/is-emirleri/",
        {
            "tahmin_kaydi_id": str(made.pk),
            "idempotency_key": "forbidden-replay",
            "baslik": "Replay",
            "aciklama": "Yasak",
        },
        format="json",
        HTTP_X_TRACE_ID="replay-trace",
    )
    assert response.status_code == 409
    assert response.data["hata"]["kod"] == "REPLAY_TAHMININDEN_IS_EMRI_OLUSTURULAMAZ"
    assert response.data["hata"]["trace_id"] == response["X-Trace-ID"]
    assert BakimIsEmri.objects.filter(tahmin_kaydi=made).count() == 0
    assert IsEmriOlayi.objects.filter(is_emri__tahmin_kaydi=made).count() == 0


def test_real_prepared_checksum_split_order_offset_and_maximum_limit():
    from apps.tahminler.replay_services import _load_selected

    first, checksum = _load_selected(split="test", offset=7, count=1000)
    second, second_checksum = _load_selected(split="test", offset=7, count=1000)
    assert checksum == second_checksum
    assert len(first) == len(second) == 1000
    assert first["_source_index"].tolist() == second["_source_index"].tolist()
    assert first["_timestamp"].is_monotonic_increasing
    assert first[["_timestamp", "_source_index"]].equals(
        second[["_timestamp", "_source_index"]]
    )


def test_missing_prepared_file_and_checksum_mismatch_are_safe(admin, machine):
    import json
    from pathlib import Path

    missing = Path("/definitely/not/a/prepared.csv")
    with patch(
        "apps.tahminler.replay_services.settings.REPLAY_PREPARED_DATASET_PATH",
        missing,
    ):
        response = client_for(admin).post(URL, create_body(machine), format="json")
    assert response.status_code == 503
    assert str(missing) not in str(response.data)

    metadata = json.dumps({"prepared_source_sha256": "0" * 64})
    metadata_path = type(
        "ChecksumMetadataPath", (), {"read_text": lambda *args, **kwargs: metadata}
    )()
    with patch(
        "apps.tahminler.replay_services.settings.REPLAY_PREPARED_METADATA_PATH",
        metadata_path,
    ):
        response = client_for(admin).post(URL, create_body(machine), format="json")
    assert response.status_code == 503
    assert "000000" not in str(response.data)
    assert ReplayOturumu.objects.count() == ReplayOgesi.objects.count() == 0


def test_broken_dataset_columns_are_controlled_session_fatal(admin, machine):
    broken = frame(1).drop(columns=["_timestamp"])
    broken["timestamp"] = None
    with patch(
        "apps.tahminler.replay_services.load_prepared_dataset", return_value=broken
    ):
        response = client_for(admin).post(URL, create_body(machine), format="json")
    assert response.status_code == 503
    assert ReplayOturumu.objects.count() == ReplayOgesi.objects.count() == 0


def test_external_machine_id_is_not_used_as_database_primary_key(admin, machine):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    item = session.ogeler.get()
    assert session.makine_id == machine.pk
    assert item.external_machine_id == "M-001"
    assert item.external_machine_id != str(machine.pk)


def test_failed_items_are_excluded_from_detail_metrics(admin, machine):
    created = create_session(admin, machine, 2)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    made = prediction(admin, machine)
    first, second = list(session.ogeler.all())
    first.durum, first.tahmin_kaydi = "BASARILI", made
    first.save()
    second.durum = "BASARISIZ"
    second.save()
    session.durum = ReplayOturumu.Durum.TAMAMLANDI
    session.save(update_fields=("durum",))
    response = client_for(admin).get(f"{URL}{session.pk}/")
    assert response.data["metrikler"]["degerlendirilen_oge_sayisi"] == 1


def test_detail_metric_uses_reliable_physical_and_experimental_twf_policy(
    admin, machine
):
    created = create_session(admin, machine, 1)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    made = prediction(admin, machine)
    ArizaTipiSnapshot.objects.bulk_create(
        [
            ArizaTipiSnapshot(
                tahmin=made,
                kod="HDF",
                olasilik=0.8,
                threshold=0.5,
                esik_asildi=True,
                operasyonel_kullanima_uygun=True,
                guvenilir_aday=False,
            ),
            ArizaTipiSnapshot(
                tahmin=made,
                kod="TWF",
                olasilik=0.8,
                threshold=0.5,
                esik_asildi=True,
                operasyonel_kullanima_uygun=False,
                guvenilir_aday=False,
            ),
        ]
    )
    item = session.ogeler.get()
    item.ground_truth_snapshot = {
        "makine_arizasi": 1,
        "HDF": 1,
        "PWF": 0,
        "OSF": 0,
        "TWF": 1,
        "RNF": 0,
    }
    item.durum, item.tahmin_kaydi = "BASARILI", made
    item.save()
    session.durum = ReplayOturumu.Durum.TAMAMLANDI
    session.save(update_fields=("durum",))
    metrics = client_for(admin).get(f"{URL}{session.pk}/").data["metrikler"]
    assert metrics["failure_types"]["HDF"]["predicted_positive"] == 0
    assert metrics["failure_types"]["HDF"]["fn"] == 1
    assert metrics["failure_types"]["TWF"]["predicted_positive"] == 1
    assert metrics["failure_types"]["TWF"]["tp"] == 1


def test_passive_user_pagination_and_internal_fields_are_safe(admin, user, machine):
    created = create_session(admin, machine, 2)
    session = ReplayOturumu.objects.get(pk=created.data["id"])
    session.adim_aktif = True
    import uuid

    session.aktif_claim_token = uuid.uuid4()
    session.save()
    item = session.ogeler.first()
    item.processing_token = uuid.uuid4()
    item.save()
    response = client_for(user).get(URL, {"page_size": 1})
    assert response.status_code == 400  # unknown query parameters are rejected
    response = client_for(user).get(f"{URL}{session.pk}/ogeler/")
    rendered = str(response.data)
    assert response.status_code == 200 and "processing_token" not in rendered
    assert "aktif_claim_token" not in rendered and "payload_fingerprint" not in rendered
    user.is_active = False
    user.save()
    assert client_for(user).get(URL).status_code == 403


def test_replay_model_constraints_and_relational_policies_are_declared():
    session_constraints = {item.name for item in ReplayOturumu._meta.constraints}
    item_constraints = {item.name for item in ReplayOgesi._meta.constraints}
    event_constraints = {item.name for item in ReplayOlayi._meta.constraints}
    assert {
        "replay_durum_gecerli",
        "replay_version_pozitif",
        "replay_toplam_1_1000",
        "replay_batch_1_25",
    } <= session_constraints
    assert {
        "replay_oge_durum_gecerli",
        "replay_oge_sira_benzersiz",
        "replay_oge_kaynak_benzersiz",
        "replay_oge_sira_pozitif",
        "replay_deneme_negatif_degil",
    } <= item_constraints
    assert {
        "replay_olay_tipi_gecerli",
        "replay_olay_version_pozitif",
        "replay_olay_ilk_sira_pozitif",
        "replay_olay_son_sira_pozitif",
    } <= event_constraints
    assert (
        ReplayOturumu._meta.get_field("makine").remote_field.on_delete.__name__
        == "PROTECT"
    )
    assert (
        ReplayOturumu._meta.get_field("olusturan").remote_field.on_delete.__name__
        == "PROTECT"
    )
    assert (
        ReplayOgesi._meta.get_field("tahmin_kaydi").remote_field.on_delete.__name__
        == "PROTECT"
    )
    assert (
        ReplayOgesi._meta.get_field("oturum").remote_field.on_delete.__name__
        == "CASCADE"
    )
