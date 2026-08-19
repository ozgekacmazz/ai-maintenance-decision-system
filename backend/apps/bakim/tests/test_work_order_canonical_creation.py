from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.bakim.api.work_order_serializers import (
    IsEmriFiltreSerializer,
    IsEmriListeSerializer,
    IsEmriOlusturmaSerializer,
    IsEmriOncelikOverrideSerializer,
)
from apps.bakim.exceptions import IsEmriCakismasiHatasi
from apps.bakim.models import BakimIsEmri, IsEmriOlayi, Makine
from apps.bakim.work_order_policy import IsEmriPolitikaHatasi
from apps.bakim.work_order_selectors import is_emri_listesi
from apps.bakim.work_order_services import (
    _canonical_karar_degerleri,
    _is_emri_oncelik_turu,
    is_emri_olustur,
    is_emri_oncelik_override,
)
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import BakimKarariSnapshot, TahminKaydi

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor():
    return Kullanici.objects.create_user(username="canonical-order-user")


@pytest.fixture
def machine():
    return Makine.objects.create(
        makine_kodu="CW-M1", ad="Canonical work order", tip="Pres", kritiklik=5
    )


def create_prediction(actor, machine, *, key, priority=None, legacy_priority="KRITIK"):
    prediction = TahminKaydi.objects.create(
        makine=machine,
        olusturan=actor,
        trace_id=f"trace-{key}",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key=key,
        payload_fingerprint="a" * 64,
        makine_kodu_snapshot=machine.makine_kodu,
        makine_adi_snapshot=machine.ad,
        kritiklik_snapshot=machine.kritiklik,
        sensor_snapshot={},
        risk_orani=0.8,
        risk_uyarisi=True,
        binary_threshold=0.2,
        binary_model_version="binary-v1",
        binary_pipeline_version="pipeline-v1",
        failure_type_durum="DEGERLENDIRILDI",
        belirsiz_fiziksel_tip=False,
        aciklanabilirlik_durum="ACIKLANDI",
    )
    canonical = (
        {
            "genel_oncelik": priority,
            "stok_katsayisi": Decimal("1.25"),
            "ham_genel_oncelik": Decimal("4.2500"),
            "genel_oncelik_formul_surumu": "general-priority-1.0.0",
        }
        if priority is not None
        else {}
    )
    BakimKarariSnapshot.objects.create(
        tahmin=prediction,
        motor_surumu="maintenance-priority-1.0.0",
        teknik_aciliyet_skoru=90,
        tedarik_riski_skoru=50,
        nihai_oncelik_skoru=82,
        oncelik_seviyesi=legacy_priority,
        ana_aksiyon="ACIL_TEKNIK_DEGERLENDIRME",
        ana_ariza_tipi="OSF",
        karar_guveni="YUKSEK",
        **canonical,
    )
    return prediction


def create_order(actor, prediction, *, key="canonical-order"):
    return is_emri_olustur(
        actor=actor,
        trace_id=f"trace-{key}",
        veriler={
            "tahmin_kaydi_id": prediction.pk,
            "idempotency_key": key,
            "baslik": "Canonical bakım",
            "aciklama": "Canonical öncelik entegrasyonu",
        },
    )


@pytest.mark.parametrize(
    ("priority", "hours"), [(1, 168), (2, 120), (3, 72), (4, 24), (5, 4)]
)
def test_canonical_create_snapshots_priority_and_uses_exact_sla(
    actor, machine, priority, hours
):
    prediction = create_prediction(
        actor, machine, key=f"canonical-{priority}", priority=priority
    )
    start = datetime(2026, 8, 19, 10, 30, tzinfo=datetime_timezone.utc)

    with patch("apps.bakim.work_order_services.timezone.now", return_value=start):
        order, repeated = create_order(actor, prediction)

    assert repeated is False
    assert order.kaynak_genel_oncelik == priority
    assert order.kaynak_genel_oncelik_formul_surumu == "general-priority-1.0.0"
    assert order.etkin_genel_oncelik == priority
    assert order.hedef_mudahale_zamani == start + timedelta(hours=hours)
    assert order.kaynak_oncelik_seviyesi == order.etkin_oncelik_seviyesi == "KRITIK"
    assert order.kaynak_teknik_aciliyet_skoru == 90
    event = order.olaylar.get()
    assert event.olay_tipi == "OLUSTURULDU"
    assert event.onceki_genel_oncelik is event.yeni_genel_oncelik is None


@pytest.mark.parametrize(
    ("legacy_priority", "hours"),
    [("DUSUK", 168), ("ORTA", 72), ("YUKSEK", 24), ("KRITIK", 4)],
)
def test_legacy_create_keeps_null_canonical_fields_and_legacy_sla(
    actor, machine, legacy_priority, hours
):
    prediction = create_prediction(
        actor,
        machine,
        key=f"legacy-{legacy_priority}",
        legacy_priority=legacy_priority,
    )
    start = datetime(2026, 8, 19, 10, 30, tzinfo=datetime_timezone.utc)

    with patch("apps.bakim.work_order_services.timezone.now", return_value=start):
        order, _ = create_order(actor, prediction, key=f"order-{legacy_priority}")

    assert order.kaynak_genel_oncelik is None
    assert order.kaynak_genel_oncelik_formul_surumu is None
    assert order.etkin_genel_oncelik is None
    assert order.kaynak_oncelik_seviyesi == legacy_priority
    assert order.etkin_oncelik_seviyesi == legacy_priority
    assert order.hedef_mudahale_zamani == start + timedelta(hours=hours)


def test_partial_canonical_decision_is_rejected_without_legacy_fallback():
    partial = SimpleNamespace(
        genel_oncelik=3,
        stok_katsayisi=None,
        ham_genel_oncelik=Decimal("3.0000"),
        genel_oncelik_formul_surumu="general-priority-1.0.0",
    )

    with pytest.raises(IsEmriCakismasiHatasi) as exc_info:
        _canonical_karar_degerleri(partial)

    assert exc_info.value.kod == "IS_EMRI_CANONICAL_KARAR_GECERSIZ"


@pytest.mark.parametrize(
    "source_field",
    ("kaynak_genel_oncelik", "kaynak_genel_oncelik_formul_surumu"),
)
def test_create_serializer_rejects_canonical_source_fields(source_field):
    serializer = IsEmriOlusturmaSerializer(
        data={
            "tahmin_kaydi_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "idempotency_key": "serializer-security",
            "baslik": "Bakım",
            "aciklama": "Kontrol",
            source_field: 3,
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors[source_field] == ["Beklenmeyen alan."]


def test_idempotent_repeat_does_not_recalculate_or_mutate_canonical_order(
    actor, machine
):
    prediction = create_prediction(actor, machine, key="idempotent", priority=4)
    with patch(
        "apps.bakim.work_order_services.genel_oncelik_hedef_mudahale_zamani"
    ) as sla:
        sla.return_value = timezone.now() + timedelta(hours=24)
        first, first_repeated = create_order(actor, prediction)
        original = (
            first.kaynak_genel_oncelik,
            first.etkin_genel_oncelik,
            first.hedef_mudahale_zamani,
        )
        second, second_repeated = create_order(actor, prediction)

    assert (first_repeated, second_repeated) == (False, True)
    assert second.pk == first.pk
    assert (
        second.kaynak_genel_oncelik,
        second.etkin_genel_oncelik,
        second.hedef_mudahale_zamani,
    ) == original
    assert sla.call_count == 1
    assert BakimIsEmri.objects.count() == IsEmriOlayi.objects.count() == 1


def test_canonical_sla_error_rolls_back_order_and_event(actor, machine):
    prediction = create_prediction(actor, machine, key="sla-error", priority=5)

    with (
        patch(
            "apps.bakim.work_order_services.genel_oncelik_hedef_mudahale_zamani",
            side_effect=IsEmriPolitikaHatasi("geçersiz SLA"),
        ),
        pytest.raises(IsEmriCakismasiHatasi) as exc_info,
    ):
        create_order(actor, prediction)

    assert exc_info.value.kod == "IS_EMRI_CANONICAL_SLA_GECERSIZ"
    assert not BakimIsEmri.objects.exists()
    assert not IsEmriOlayi.objects.exists()


def test_terminal_order_allows_new_snapshot_without_mutating_old_order(actor, machine):
    prediction = create_prediction(actor, machine, key="terminal", priority=3)
    old, _ = create_order(actor, prediction, key="terminal-old")
    old.durum = BakimIsEmri.Durum.TAMAMLANDI
    old.save(update_fields=("durum",))
    old_values = (old.etkin_genel_oncelik, old.hedef_mudahale_zamani)

    new, repeated = create_order(actor, prediction, key="terminal-new")
    old.refresh_from_db()

    assert repeated is False
    assert new.pk != old.pk
    assert new.kaynak_genel_oncelik == new.etkin_genel_oncelik == 3
    assert (old.etkin_genel_oncelik, old.hedef_mudahale_zamani) == old_values
    assert BakimIsEmri.objects.count() == IsEmriOlayi.objects.count() == 2


@pytest.mark.parametrize(
    ("priority", "hours"), [(1, 168), (2, 120), (3, 72), (4, 24), (5, 4)]
)
def test_canonical_override_updates_effective_priority_sla_and_audit(
    actor, machine, priority, hours
):
    actor.rol = Kullanici.Rol.ADMIN
    actor.save(update_fields=("rol",))
    initial_priority = 2 if priority == 3 else 3
    prediction = create_prediction(
        actor, machine, key=f"override-{priority}", priority=initial_priority
    )
    order, _ = create_order(actor, prediction, key=f"override-order-{priority}")
    source_values = (
        order.kaynak_genel_oncelik,
        order.kaynak_genel_oncelik_formul_surumu,
        order.etkin_oncelik_seviyesi,
    )
    start = datetime(2026, 8, 19, 12, 0, tzinfo=datetime_timezone.utc)

    with patch("apps.bakim.work_order_services.timezone.now", return_value=start):
        changed = is_emri_oncelik_override(
            order_id=order.pk,
            actor=actor,
            trace_id="canonical-override",
            expected_version=1,
            general_priority=priority,
            reason="Plan değişti",
        )

    assert changed.etkin_genel_oncelik == priority
    assert changed.hedef_mudahale_zamani == start + timedelta(hours=hours)
    assert changed.version == 2
    assert (
        changed.kaynak_genel_oncelik,
        changed.kaynak_genel_oncelik_formul_surumu,
        changed.etkin_oncelik_seviyesi,
    ) == source_values
    event = changed.olaylar.get(version=2)
    assert (event.onceki_genel_oncelik, event.yeni_genel_oncelik) == (
        initial_priority,
        priority,
    )
    assert event.onceki_oncelik is event.yeni_oncelik is None


def test_legacy_override_keeps_canonical_fields_null_and_legacy_audit(actor, machine):
    actor.rol = Kullanici.Rol.ADMIN
    actor.save(update_fields=("rol",))
    prediction = create_prediction(actor, machine, key="legacy-override")
    order, _ = create_order(actor, prediction, key="legacy-override-order")
    start = datetime(2026, 8, 19, 12, 0, tzinfo=datetime_timezone.utc)

    with patch("apps.bakim.work_order_services.timezone.now", return_value=start):
        changed = is_emri_oncelik_override(
            order_id=order.pk,
            actor=actor,
            trace_id="legacy-override",
            expected_version=1,
            priority="ORTA",
            reason="Plan değişti",
        )

    assert changed.etkin_oncelik_seviyesi == "ORTA"
    assert changed.hedef_mudahale_zamani == start + timedelta(hours=72)
    assert changed.kaynak_genel_oncelik is None
    assert changed.kaynak_genel_oncelik_formul_surumu is None
    assert changed.etkin_genel_oncelik is None
    event = changed.olaylar.get(version=2)
    assert (event.onceki_oncelik, event.yeni_oncelik) == ("KRITIK", "ORTA")
    assert event.onceki_genel_oncelik is event.yeni_genel_oncelik is None


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"genel_oncelik": 3, "etkin_oncelik_seviyesi": "ORTA"},
        {"genel_oncelik": 0},
        {"genel_oncelik": 6},
        {"genel_oncelik": -1},
        {"genel_oncelik": 1.5},
        {"genel_oncelik": "3"},
        {"genel_oncelik": True},
        {"genel_oncelik": None},
    ],
)
def test_override_serializer_rejects_ambiguous_missing_or_invalid_priority(data):
    serializer = IsEmriOncelikOverrideSerializer(
        data={"beklenen_version": 1, "override_nedeni": "Plan", **data}
    )

    assert serializer.is_valid() is False
    assert "genel_oncelik" in serializer.errors


@pytest.mark.parametrize(
    "field", ("kaynak_genel_oncelik", "kaynak_genel_oncelik_formul_surumu")
)
def test_override_serializer_rejects_direct_source_field_write(field):
    serializer = IsEmriOncelikOverrideSerializer(
        data={
            "beklenen_version": 1,
            "override_nedeni": "Plan",
            "genel_oncelik": 4,
            field: 5,
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors[field] == ["Beklenmeyen alan."]


def test_partial_canonical_order_classification_is_rejected():
    partial = SimpleNamespace(
        kaynak_genel_oncelik=3,
        kaynak_genel_oncelik_formul_surumu=None,
        etkin_genel_oncelik=3,
    )

    with pytest.raises(IsEmriCakismasiHatasi) as exc_info:
        _is_emri_oncelik_turu(partial)

    assert exc_info.value.kod == "IS_EMRI_CANONICAL_ALANLAR_TUTARSIZ"


def test_override_rejects_wrong_priority_family_without_mutation(actor, machine):
    actor.rol = Kullanici.Rol.ADMIN
    actor.save(update_fields=("rol",))
    canonical_prediction = create_prediction(
        actor, machine, key="wrong-family", priority=3
    )
    canonical, _ = create_order(actor, canonical_prediction, key="wrong-family-order")
    original = (canonical.version, canonical.hedef_mudahale_zamani)

    with pytest.raises(IsEmriCakismasiHatasi) as exc_info:
        is_emri_oncelik_override(
            order_id=canonical.pk,
            actor=actor,
            trace_id="wrong-family",
            expected_version=1,
            priority="ORTA",
            reason="Plan",
        )

    canonical.refresh_from_db()
    assert exc_info.value.kod == "IS_EMRI_CANONICAL_OVERRIDE_ALANI_GECERSIZ"
    assert (canonical.version, canonical.hedef_mudahale_zamani) == original
    assert canonical.olaylar.count() == 1


def test_canonical_noop_is_rejected_without_deadline_version_or_event(actor, machine):
    actor.rol = Kullanici.Rol.ADMIN
    actor.save(update_fields=("rol",))
    prediction = create_prediction(actor, machine, key="override-noop", priority=3)
    order, _ = create_order(actor, prediction, key="override-noop-order")
    original_deadline = order.hedef_mudahale_zamani

    with pytest.raises(IsEmriCakismasiHatasi):
        is_emri_oncelik_override(
            order_id=order.pk,
            actor=actor,
            trace_id="noop",
            expected_version=1,
            general_priority=3,
            reason="Aynı",
        )

    order.refresh_from_db()
    assert (order.version, order.hedef_mudahale_zamani) == (1, original_deadline)
    assert order.olaylar.count() == 1


def test_canonical_override_sla_error_rolls_back_all_changes(actor, machine):
    actor.rol = Kullanici.Rol.ADMIN
    actor.save(update_fields=("rol",))
    prediction = create_prediction(actor, machine, key="override-sla", priority=3)
    order, _ = create_order(actor, prediction, key="override-sla-order")
    original = (order.etkin_genel_oncelik, order.hedef_mudahale_zamani, order.version)

    with (
        patch(
            "apps.bakim.work_order_services.genel_oncelik_hedef_mudahale_zamani",
            side_effect=IsEmriPolitikaHatasi("geçersiz"),
        ),
        pytest.raises(IsEmriCakismasiHatasi) as exc_info,
    ):
        is_emri_oncelik_override(
            order_id=order.pk,
            actor=actor,
            trace_id="sla-error",
            expected_version=1,
            general_priority=5,
            reason="Plan",
        )

    order.refresh_from_db()
    assert exc_info.value.kod == "IS_EMRI_CANONICAL_SLA_GECERSIZ"
    assert (
        order.etkin_genel_oncelik,
        order.hedef_mudahale_zamani,
        order.version,
    ) == original
    assert order.olaylar.count() == 1


def test_list_response_exposes_canonical_fields_and_legacy_nulls(actor, machine):
    canonical_prediction = create_prediction(
        actor, machine, key="api-canonical", priority=4
    )
    legacy_prediction = create_prediction(actor, machine, key="api-legacy")
    canonical, _ = create_order(actor, canonical_prediction, key="api-canonical-order")
    legacy, _ = create_order(actor, legacy_prediction, key="api-legacy-order")

    data = IsEmriListeSerializer(
        [canonical, legacy], many=True, context={"now": timezone.now()}
    ).data

    assert data[0]["kaynak_genel_oncelik"] == 4
    assert data[0]["kaynak_genel_oncelik_formul_surumu"] == "general-priority-1.0.0"
    assert data[0]["etkin_genel_oncelik"] == 4
    assert data[1]["kaynak_genel_oncelik"] is None
    assert data[1]["kaynak_genel_oncelik_formul_surumu"] is None
    assert data[1]["etkin_genel_oncelik"] is None


@pytest.mark.parametrize("invalid", [0, 6, -1, 1.5, "3", ""])
def test_general_priority_filter_rejects_invalid_values(invalid):
    serializer = IsEmriFiltreSerializer(data={"genel_oncelik": invalid})

    assert serializer.is_valid() is False
    assert "genel_oncelik" in serializer.errors


@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        ("etkin_genel_oncelik", [2, 5, None]),
        ("-etkin_genel_oncelik", [5, 2, None]),
    ],
)
def test_general_priority_ordering_is_stable_and_nulls_last(
    actor, machine, ordering, expected
):
    for priority in (5, 2, None):
        suffix = str(priority) if priority is not None else "legacy"
        prediction = create_prediction(
            actor, machine, key=f"sort-{suffix}", priority=priority
        )
        create_order(actor, prediction, key=f"sort-order-{suffix}")

    results = list(
        is_emri_listesi(filtreler={"sirala": ordering}).values_list(
            "etkin_genel_oncelik", flat=True
        )
    )

    assert results == expected
