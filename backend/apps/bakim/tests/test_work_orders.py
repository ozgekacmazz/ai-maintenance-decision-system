from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bakim.exceptions import EszamanliGuncellemeHatasi, IsEmriCakismasiHatasi
from apps.bakim.models import BakimIsEmri, IsEmriOlayi, Makine, Parca
from apps.bakim.work_order_policy import (
    ACTIVE_STATES,
    ALLOWED_TRANSITIONS,
    TERMINAL_STATES,
    IsEmriPolitikaHatasi,
    gecikmis_mi,
    gecisi_dogrula,
)
from apps.bakim.work_order_services import (
    is_emri_ata,
    is_emri_durum_gecisi,
    is_emri_olustur,
)
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import (
    ArizaTipiSnapshot,
    BakimKarariSnapshot,
    ErpSnapshot,
    TahminKaydi,
)

pytestmark = pytest.mark.django_db
URL = "/api/bakim/is-emirleri/"


@pytest.fixture
def admin():
    return Kullanici.objects.create_user(username="admin-wo", rol="ADMIN")


@pytest.fixture
def user():
    return Kullanici.objects.create_user(username="user-wo", rol="USER")


@pytest.fixture
def technician():
    return Kullanici.objects.create_user(username="tech-wo", rol="USER")


@pytest.fixture
def machine():
    return Makine.objects.create(
        makine_kodu="WO-M1", ad="Pres", tip="Pres", kritiklik=5
    )


@pytest.fixture
def prediction(user, machine):
    record = TahminKaydi.objects.create(
        makine=machine,
        olusturan=user,
        trace_id="trace",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key="prediction-key",
        payload_fingerprint="a" * 64,
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
        motor_surumu="maintenance-priority-1.0.0",
        teknik_aciliyet_skoru=90,
        tedarik_riski_skoru=50,
        nihai_oncelik_skoru=82,
        oncelik_seviyesi="KRITIK",
        ana_aksiyon="ACIL_TEKNIK_DEGERLENDIRME",
        ana_ariza_tipi="OSF",
        karar_guveni="YUKSEK",
    )
    return record


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def create_payload(prediction, key="wo-key"):
    return {
        "tahmin_kaydi_id": str(prediction.pk),
        "idempotency_key": key,
        "baslik": "Öncelikli bakım incelemesi",
        "aciklama": "Saha kontrolü planlandı.",
    }


def create_order(actor, prediction, key="wo-key"):
    response = client_for(actor).post(
        URL, create_payload(prediction, key), format="json"
    )
    assert response.status_code == 201
    return response


def test_state_machine_allows_exact_transition_matrix_without_mutating_input():
    values = {
        "neden": "kontrol",
        "bekleme_nedeni": "parça",
        "tamamlama_notu": "bitti",
        "iptal_nedeni": "iptal",
    }
    original = deepcopy(values)
    for source, targets in ALLOWED_TRANSITIONS.items():
        for target in targets:
            data = values
            gecisi_dogrula(
                mevcut_durum=source, hedef_durum=target, atanan_var=True, veriler=data
            )
    assert values == original
    assert ACTIVE_STATES.isdisjoint(TERMINAL_STATES)


@pytest.mark.parametrize("source", ALLOWED_TRANSITIONS)
def test_same_state_is_rejected(source):
    with pytest.raises(IsEmriPolitikaHatasi):
        gecisi_dogrula(
            mevcut_durum=source, hedef_durum=source, atanan_var=True, veriler={}
        )


def test_create_snapshots_decision_sla_number_and_event(user, prediction):
    response = create_order(user, prediction)
    assert response.data["durum"] == "ACIK"
    assert response.data["version"] == 1
    assert response.data["is_emri_numarasi"].startswith("WO-")
    assert response.data["kaynak_karar"]["nihai_oncelik_skoru"] == 82
    order = BakimIsEmri.objects.get(pk=response.data["id"])
    assert (
        timedelta(hours=3, minutes=59)
        < order.hedef_mudahale_zamani - order.olusturulma_zamani
        <= timedelta(hours=4)
    )
    assert list(order.olaylar.values_list("olay_tipi", "version")) == [
        ("OLUSTURULDU", 1)
    ]


def test_idempotent_repeat_and_conflicts(user, prediction):
    client = client_for(user)
    payload = create_payload(prediction)
    first = client.post(URL, payload, format="json")
    repeat = client.post(URL, payload, format="json")
    changed = deepcopy(payload)
    changed["baslik"] = "Farklı"
    conflict = client.post(URL, changed, format="json")
    duplicate = client.post(
        URL, create_payload(prediction, "different-key"), format="json"
    )
    assert (first.status_code, repeat.status_code) == (201, 200)
    assert first.data["id"] == repeat.data["id"]
    assert IsEmriOlayi.objects.count() == 1
    assert conflict.status_code == duplicate.status_code == 409
    assert conflict.data["hata"]["kod"] == "IDEMPOTENCY_CAKISMASI"
    assert duplicate.data["hata"]["kod"] == "IS_EMRI_AKTIF_KAYIT_MEVCUT"


def test_legacy_prediction_without_decision_is_rejected(user, machine):
    legacy = TahminKaydi.objects.create(
        makine=machine,
        olusturan=user,
        trace_id="t",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key="legacy",
        payload_fingerprint="b" * 64,
        makine_kodu_snapshot="WO-M1",
        makine_adi_snapshot="Pres",
        kritiklik_snapshot=5,
        sensor_snapshot={},
        risk_orani=0.1,
        risk_uyarisi=False,
        binary_threshold=0.2,
        binary_model_version="v",
        binary_pipeline_version="p",
        failure_type_durum="LOW",
        belirsiz_fiziksel_tip=False,
        aciklanabilirlik_durum="LOW",
    )
    response = client_for(user).post(URL, create_payload(legacy), format="json")
    assert response.status_code == 409
    assert response.data["hata"]["kod"] == "IS_EMRI_KARARI_BULUNAMADI"


def test_admin_assigns_and_stale_version_is_rejected(
    admin, user, technician, prediction
):
    created = create_order(user, prediction)
    endpoint = f"{URL}{created.data['id']}/ata/"
    assigned = client_for(admin).post(
        endpoint,
        {
            "atanan_kullanici_id": technician.pk,
            "beklenen_version": 1,
            "not": "Mekanik ekip",
        },
        format="json",
    )
    stale = client_for(admin).post(
        endpoint, {"atanan_kullanici_id": user.pk, "beklenen_version": 1}, format="json"
    )
    unauthorized = client_for(user).post(
        endpoint, {"atanan_kullanici_id": user.pk, "beklenen_version": 2}, format="json"
    )
    assert assigned.status_code == 200 and assigned.data["durum"] == "ATANDI"
    assert assigned.data["version"] == 2
    assert stale.status_code == 409
    assert stale.data["hata"]["kod"] == "ESZAMANLI_GUNCELLEME_CAKISMASI"
    assert unauthorized.status_code == 403


def test_assigned_user_runs_wait_resume_complete_workflow(
    admin, user, technician, prediction
):
    created = create_order(user, prediction)
    order_id = created.data["id"]
    client_for(admin).post(
        f"{URL}{order_id}/ata/",
        {"atanan_kullanici_id": technician.pk, "beklenen_version": 1},
        format="json",
    )
    tech = client_for(technician)
    endpoint = f"{URL}{order_id}/durum-gecisi/"
    started = tech.post(
        endpoint,
        {"beklenen_version": 2, "hedef_durum": "DEVAM_EDIYOR", "neden": "Başlandı"},
        format="json",
    )
    first_start = started.data["gercek_baslangic_zamani"]
    waiting = tech.post(
        endpoint,
        {"beklenen_version": 3, "hedef_durum": "BEKLEMEDE", "bekleme_nedeni": "Parça"},
        format="json",
    )
    resumed = tech.post(
        endpoint,
        {"beklenen_version": 4, "hedef_durum": "DEVAM_EDIYOR", "neden": "Parça geldi"},
        format="json",
    )
    completed = tech.post(
        endpoint,
        {
            "beklenen_version": 5,
            "hedef_durum": "TAMAMLANDI",
            "tamamlama_notu": "Kontrol tamamlandı",
        },
        format="json",
    )
    terminal = tech.post(
        endpoint,
        {"beklenen_version": 6, "hedef_durum": "BEKLEMEDE", "bekleme_nedeni": "x"},
        format="json",
    )
    assert waiting.data["durum"] == "BEKLEMEDE"
    assert resumed.data["gercek_baslangic_zamani"] == first_start
    assert (
        completed.data["durum"] == "TAMAMLANDI" and completed.data["tamamlanma_zamani"]
    )
    assert terminal.status_code == 409
    assert BakimIsEmri.objects.get(pk=order_id).olaylar.count() == 6


def test_only_admin_can_override_priority_and_source_stays_same(
    admin, user, prediction
):
    created = create_order(user, prediction)
    endpoint = f"{URL}{created.data['id']}/oncelik-override/"
    denied = client_for(user).post(
        endpoint,
        {
            "beklenen_version": 1,
            "etkin_oncelik_seviyesi": "ORTA",
            "override_nedeni": "Plan",
        },
        format="json",
    )
    changed = client_for(admin).post(
        endpoint,
        {
            "beklenen_version": 1,
            "etkin_oncelik_seviyesi": "ORTA",
            "override_nedeni": "Planlı duruş",
        },
        format="json",
    )
    assert denied.status_code == 403
    assert changed.status_code == 200
    assert changed.data["etkin_oncelik_seviyesi"] == "ORTA"
    assert changed.data["kaynak_oncelik_seviyesi"] == "KRITIK"
    assert changed.data["version"] == 2


def test_overdue_boundary_and_terminal_policy():
    now = timezone.now()
    assert gecikmis_mi(durum="ACIK", hedef=now, simdi=now) is False
    assert (
        gecikmis_mi(durum="ACIK", hedef=now - timedelta(microseconds=1), simdi=now)
        is True
    )
    assert (
        gecikmis_mi(durum="TAMAMLANDI", hedef=now - timedelta(days=1), simdi=now)
        is False
    )


def test_event_is_immutable(user, prediction):
    created = create_order(user, prediction)
    event = IsEmriOlayi.objects.get(is_emri_id=created.data["id"])
    event.aciklama_snapshot = "değiştir"
    with pytest.raises(ValueError):
        event.save()
    with pytest.raises(ValueError):
        IsEmriOlayi.objects.filter(pk=event.pk).update(aciklama_snapshot="x")


def test_db_constraints_for_active_order_and_version(user, prediction):
    created = create_order(user, prediction)
    existing = BakimIsEmri.objects.get(pk=created.data["id"])
    with pytest.raises(IntegrityError), transaction.atomic():
        BakimIsEmri.objects.create(
            **{
                field.name: getattr(existing, field.name)
                for field in BakimIsEmri._meta.fields
                if field.name
                not in {
                    "id",
                    "is_emri_numarasi",
                    "idempotency_key",
                    "olusturulma_zamani",
                    "guncellenme_zamani",
                }
            },
            is_emri_numarasi="WO-DUPLICATE",
            idempotency_key="other",
        )


def test_list_detail_filters_unknown_and_methods(user, prediction):
    created = create_order(user, prediction)
    client = client_for(user)
    listing = client.get(
        URL, {"durum": "ACIK", "etkin_oncelik_seviyesi": "KRITIK", "gecikmis": "false"}
    )
    detail = client.get(f"{URL}{created.data['id']}/")
    assert listing.status_code == 200 and listing.data["count"] == 1
    assert detail.status_code == 200 and len(detail.data["olaylar"]) == 1
    assert client.get(URL, {"bilinmeyen": "x"}).status_code == 400
    assert client.get(URL, {"sirala": "unsafe"}).status_code == 400
    for method in (client.put, client.patch, client.delete):
        assert (
            method(f"{URL}{created.data['id']}/", {}, format="json").status_code == 405
        )


def test_list_returns_action_and_deterministic_erp_snapshots(user, prediction):
    failure = ArizaTipiSnapshot.objects.create(
        tahmin=prediction,
        kod="OSF",
        olasilik=0.9,
        threshold=0.5,
        esik_asildi=True,
        operasyonel_kullanima_uygun=True,
        guvenilir_aday=True,
        siralama=1,
    )
    for code, name, amount in (("PRC-B", "Rulman B", 1), ("PRC-A", "Rulman A", 2)):
        part = Parca.objects.create(parca_kodu=code, ad=name)
        ErpSnapshot.objects.create(
            tahmin=prediction,
            ariza_tipi=failure,
            parca=part,
            parca_kodu_snapshot=code,
            parca_adi_snapshot=name,
            gerekli_miktar=amount,
            stok_durumu="MEVCUT",
            stok_yeterli=True,
            deneysel=False,
            onerilen_aksiyon_snapshot="Parçayı kontrol et",
        )
    created = create_order(user, prediction)
    client = client_for(user)

    listing = client.get(URL)
    detail = client.get(f"{URL}{created.data['id']}/")
    row = listing.data["results"][0]

    assert row["ana_aksiyon"] == detail.data["kaynak_karar"]["ana_aksiyon"]
    assert row["erp_ozeti"] == detail.data["erp_ozeti"]
    assert [item["parca_kodu"] for item in row["erp_ozeti"]] == ["PRC-A", "PRC-B"]
    assert row["erp_ozeti"][0]["gerekli_miktar"] == 2
    assert row["etkin_oncelik_seviyesi"] == "KRITIK"


def test_list_returns_safe_empty_erp_contract(user, prediction):
    create_order(user, prediction)

    row = client_for(user).get(URL).data["results"][0]

    assert row["ana_aksiyon"] == "ACIL_TEKNIK_DEGERLENDIRME"
    assert row["erp_ozeti"] == []


def test_auth_contract(prediction, user):
    assert APIClient().get(URL).status_code == 401
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert client_for(user).get(URL).status_code == 403


def test_query_counts_are_bounded(user, prediction, django_assert_max_num_queries):
    created = create_order(user, prediction)
    client = client_for(user)
    # Liste parçaları tek bir prefetch sorgusuyla alır; satır başına sorgu üretmez.
    with django_assert_max_num_queries(5):
        assert client.get(URL).status_code == 200
    with django_assert_max_num_queries(5):
        assert client.get(f"{URL}{created.data['id']}/").status_code == 200


def _concurrent_create(barrier, user_id, prediction_id, key):
    close_old_connections()
    try:
        actor = Kullanici.objects.get(pk=user_id)
        barrier.wait()
        order, repeated = is_emri_olustur(
            actor=actor,
            trace_id="concurrent",
            veriler={
                "tahmin_kaydi_id": prediction_id,
                "idempotency_key": key,
                "baslik": "Eşzamanlı bakım",
                "aciklama": "Kontrol",
            },
        )
        return "ok", order.pk, repeated
    except IsEmriCakismasiHatasi as exc:
        return "conflict", exc.kod, None
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_idempotency_key_creates_one_order(user, prediction):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _concurrent_create(barrier, user.pk, prediction.pk, "same"),
                range(2),
            )
        )
    assert {item[0] for item in results} == {"ok"}
    assert {item[1] for item in results} == {BakimIsEmri.objects.get().pk}
    assert sorted(item[2] for item in results) == [False, True]
    assert BakimIsEmri.objects.count() == IsEmriOlayi.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_different_keys_allow_only_one_active_order(user, prediction):
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_concurrent_create, barrier, user.pk, prediction.pk, key)
            for key in ("key-a", "key-b")
        ]
        results = [future.result() for future in futures]
    assert sorted(item[0] for item in results) == ["conflict", "ok"]
    assert BakimIsEmri.objects.count() == IsEmriOlayi.objects.count() == 1


def _concurrent_start(barrier, order_id, actor_id):
    close_old_connections()
    try:
        actor = Kullanici.objects.get(pk=actor_id)
        barrier.wait()
        result = is_emri_durum_gecisi(
            order_id=order_id,
            actor=actor,
            trace_id="concurrent",
            expected_version=2,
            target="DEVAM_EDIYOR",
            data={"neden": "Başla"},
        )
        return "ok", result.version
    except EszamanliGuncellemeHatasi:
        return "conflict", None
    finally:
        close_old_connections()


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_version_only_one_transition_wins(
    admin, user, technician, prediction
):
    order = is_emri_olustur(
        actor=user, trace_id="t", veriler=create_payload(prediction)
    )[0]
    is_emri_ata(
        order_id=order.pk,
        actor=admin,
        trace_id="t",
        expected_version=1,
        assignee=technician,
    )
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: _concurrent_start(barrier, order.pk, technician.pk), range(2)
            )
        )
    assert sorted(item[0] for item in results) == ["conflict", "ok"]
    order.refresh_from_db()
    assert order.version == 3
    assert order.olaylar.count() == 3
