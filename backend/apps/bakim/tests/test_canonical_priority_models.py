import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bakim.models import BakimIsEmri, IsEmriOlayi, Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import TahminKaydi

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor():
    return Kullanici.objects.create_user(username="canonical-priority-user")


@pytest.fixture
def machine():
    return Makine.objects.create(
        makine_kodu="CP-M1", ad="Canonical pres", tip="Pres", kritiklik=5
    )


@pytest.fixture
def prediction(actor, machine):
    return TahminKaydi.objects.create(
        makine=machine,
        olusturan=actor,
        trace_id="canonical-priority-trace",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key="canonical-priority-prediction",
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


def create_order(actor, machine, prediction, **overrides):
    values = {
        "is_emri_numarasi": "WO-CANONICAL-1",
        "tahmin_kaydi": prediction,
        "makine": machine,
        "olusturan": actor,
        "baslik": "Canonical öncelik testi",
        "aciklama": "Şema kısıtları doğrulanıyor.",
        "idempotency_key": "canonical-priority-order",
        "payload_fingerprint": "b" * 64,
        "politika_surumu": "work-order-policy-1.0.0",
        "kaynak_motor_surumu": "maintenance-priority-1.0.0",
        "kaynak_teknik_aciliyet_skoru": 90,
        "kaynak_tedarik_riski_skoru": 50,
        "kaynak_nihai_oncelik_skoru": 82,
        "kaynak_oncelik_seviyesi": "KRITIK",
        "kaynak_ana_aksiyon": "ACIL_TEKNIK_DEGERLENDIRME",
        "kaynak_karar_guveni": "YUKSEK",
        "kaynak_ana_ariza_tipi": "OSF",
        "etkin_oncelik_seviyesi": "KRITIK",
        "hedef_mudahale_zamani": timezone.now(),
    }
    values.update(overrides)
    return BakimIsEmri.objects.create(**values)


def create_event(order, actor, **overrides):
    values = {
        "is_emri": order,
        "olay_tipi": "OLUSTURULDU",
        "yeni_durum": "ACIK",
        "gerceklestiren": actor,
        "gerceklestiren_username_snapshot": actor.username,
        "trace_id": "canonical-event-trace",
        "version": 1,
    }
    values.update(overrides)
    return IsEmriOlayi.objects.create(**values)


def assert_constraint_rejects(call):
    with pytest.raises(IntegrityError), transaction.atomic():
        call()


def test_legacy_is_emri_canonical_alanlar_olmadan_gecerlidir(
    actor, machine, prediction
):
    order = create_order(actor, machine, prediction)

    assert order.kaynak_genel_oncelik is None
    assert order.kaynak_genel_oncelik_formul_surumu is None
    assert order.etkin_genel_oncelik is None
    assert order.kaynak_oncelik_seviyesi == order.etkin_oncelik_seviyesi == "KRITIK"


@pytest.mark.parametrize(("kaynak", "etkin"), [(1, 1), (3, 4), (5, 5)])
def test_canonical_is_emri_1_5_araligini_ve_farkli_etkin_degeri_kabul_eder(
    actor, machine, prediction, kaynak, etkin
):
    order = create_order(
        actor,
        machine,
        prediction,
        kaynak_genel_oncelik=kaynak,
        kaynak_genel_oncelik_formul_surumu="general-priority-1.0.0",
        etkin_genel_oncelik=etkin,
    )

    assert (order.kaynak_genel_oncelik, order.etkin_genel_oncelik) == (kaynak, etkin)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "kaynak_genel_oncelik": 0,
            "kaynak_genel_oncelik_formul_surumu": "v",
            "etkin_genel_oncelik": 1,
        },
        {
            "kaynak_genel_oncelik": 1,
            "kaynak_genel_oncelik_formul_surumu": "v",
            "etkin_genel_oncelik": 6,
        },
        {"kaynak_genel_oncelik": 1},
        {"kaynak_genel_oncelik_formul_surumu": "v"},
        {"etkin_genel_oncelik": 1},
        {
            "kaynak_genel_oncelik": 1,
            "kaynak_genel_oncelik_formul_surumu": "",
            "etkin_genel_oncelik": 1,
        },
    ],
)
def test_canonical_is_emri_gecersiz_kombinasyonlari_reddeder(
    actor, machine, prediction, overrides
):
    assert_constraint_rejects(
        lambda: create_order(actor, machine, prediction, **overrides)
    )


def test_is_emri_canonical_alanlari_model_katmaninda_degistirilebilir(
    actor, machine, prediction
):
    order = create_order(
        actor,
        machine,
        prediction,
        kaynak_genel_oncelik=3,
        kaynak_genel_oncelik_formul_surumu="general-priority-1.0.0",
        etkin_genel_oncelik=3,
    )
    order.kaynak_genel_oncelik = 4
    order.etkin_genel_oncelik = 5
    order.save(update_fields=("kaynak_genel_oncelik", "etkin_genel_oncelik"))
    order.refresh_from_db()

    assert (order.kaynak_genel_oncelik, order.etkin_genel_oncelik) == (4, 5)


def test_legacy_is_emri_olayi_canonical_alanlar_olmadan_gecerlidir(
    actor, machine, prediction
):
    event = create_event(create_order(actor, machine, prediction), actor)

    assert event.onceki_genel_oncelik is event.yeni_genel_oncelik is None


def test_is_emri_olayi_canonical_cifti_kabul_eder(actor, machine, prediction):
    event = create_event(
        create_order(actor, machine, prediction),
        actor,
        onceki_genel_oncelik=2,
        yeni_genel_oncelik=5,
    )

    assert (event.onceki_genel_oncelik, event.yeni_genel_oncelik) == (2, 5)


@pytest.mark.parametrize(
    "overrides",
    [
        {"onceki_genel_oncelik": 1},
        {"yeni_genel_oncelik": 1},
        {"onceki_genel_oncelik": 0, "yeni_genel_oncelik": 1},
        {"onceki_genel_oncelik": 1, "yeni_genel_oncelik": 6},
    ],
)
def test_is_emri_olayi_gecersiz_canonical_degerleri_reddeder(
    actor, machine, prediction, overrides
):
    order = create_order(actor, machine, prediction)
    assert_constraint_rejects(lambda: create_event(order, actor, **overrides))


def test_is_emri_olayi_snapshot_olarak_degistirilemez(actor, machine, prediction):
    event = create_event(
        create_order(actor, machine, prediction),
        actor,
        onceki_genel_oncelik=2,
        yeni_genel_oncelik=3,
    )
    event.yeni_genel_oncelik = 4

    with pytest.raises(ValueError):
        event.save()
    with pytest.raises(ValueError):
        IsEmriOlayi.objects.filter(pk=event.pk).update(yeni_genel_oncelik=4)
