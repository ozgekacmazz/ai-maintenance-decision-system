from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bakim.models import Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.genel_oncelik import genel_oncelik_hesapla
from apps.tahminler.models import BakimKarariSnapshot, TahminKaydi

pytestmark = pytest.mark.django_db


@pytest.fixture
def tahmin():
    kullanici = Kullanici.objects.create_user(
        username="canonical-snapshot", password="unused"
    )
    makine = Makine.objects.create(
        makine_kodu="M-CANONICAL", ad="Canonical", tip="Test", kritiklik=5
    )
    return TahminKaydi.objects.create(
        makine=makine,
        olusturan=kullanici,
        trace_id="canonical-trace",
        kaynak="MANUEL",
        olcum_zamani=timezone.now(),
        idempotency_key="canonical-key",
        payload_fingerprint="a" * 64,
        makine_kodu_snapshot=makine.makine_kodu,
        makine_adi_snapshot=makine.ad,
        kritiklik_snapshot=makine.kritiklik,
        sensor_snapshot={},
        risk_orani=0.6,
        risk_uyarisi=True,
        binary_threshold=0.2,
        binary_model_version="binary-v",
        binary_pipeline_version="pipeline-v",
        failure_type_durum="DEGERLENDIRILDI",
        belirsiz_fiziksel_tip=False,
        aciklanabilirlik_durum="ACIKLANDI",
    )


def karar_degerleri(tahmin, **overrides):
    degerler = {
        "tahmin": tahmin,
        "motor_surumu": "maintenance-priority-1.0.0",
        "teknik_aciliyet_skoru": 50,
        "tedarik_riski_skoru": 50,
        "nihai_oncelik_skoru": 50,
        "oncelik_seviyesi": "YUKSEK",
        "ana_aksiyon": "ONCELIKLI_BAKIM_PLANLA",
        "karar_guveni": "YUKSEK",
    }
    degerler.update(overrides)
    return degerler


def canonical_degerler():
    sonuc = genel_oncelik_hesapla(
        risk_orani="0.6", makine_kritikligi=5, tedarik_riski_skoru=50
    )
    return {
        "genel_oncelik": sonuc.genel_oncelik,
        "stok_katsayisi": sonuc.stok_katsayisi,
        "ham_genel_oncelik": sonuc.ham_genel_oncelik,
        "genel_oncelik_formul_surumu": sonuc.formul_surumu,
    }


def test_legacy_snapshot_canonical_alanlar_olmadan_saklanir(tahmin):
    karar = BakimKarariSnapshot.objects.create(**karar_degerleri(tahmin))
    karar.refresh_from_db()

    assert karar.genel_oncelik is None
    assert karar.stok_katsayisi is None
    assert karar.ham_genel_oncelik is None
    assert karar.genel_oncelik_formul_surumu is None
    assert karar.nihai_oncelik_skoru == 50
    assert karar.oncelik_seviyesi == "YUKSEK"


def test_b1_sonucu_canonical_snapshot_olarak_hassasiyetiyle_saklanir(tahmin):
    karar = BakimKarariSnapshot.objects.create(
        **karar_degerleri(tahmin, **canonical_degerler())
    )
    karar.refresh_from_db()

    assert karar.genel_oncelik == 3
    assert karar.stok_katsayisi == Decimal("1.50")
    assert karar.ham_genel_oncelik == Decimal("4.5000")
    assert karar.genel_oncelik_formul_surumu == "general-priority-1.0.0"


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("genel_oncelik", 0),
        ("genel_oncelik", 6),
        ("stok_katsayisi", Decimal("0.99")),
        ("stok_katsayisi", Decimal("2.01")),
        ("ham_genel_oncelik", Decimal("-0.0001")),
        ("ham_genel_oncelik", Decimal("10.0001")),
    ],
)
def test_canonical_aralik_constraintleri(tahmin, alan, deger):
    canonical = canonical_degerler()
    canonical[alan] = deger
    with pytest.raises(IntegrityError), transaction.atomic():
        BakimKarariSnapshot.objects.create(**karar_degerleri(tahmin, **canonical))


@pytest.mark.parametrize(
    "canonical",
    [
        {"genel_oncelik": 3},
        {
            "genel_oncelik": 3,
            "stok_katsayisi": Decimal("1.50"),
            "ham_genel_oncelik": Decimal("4.5000"),
        },
        {
            "stok_katsayisi": Decimal("1.50"),
            "genel_oncelik_formul_surumu": "general-priority-1.0.0",
        },
    ],
)
def test_canonical_alanlar_kismen_dolu_olamaz(tahmin, canonical):
    with pytest.raises(IntegrityError), transaction.atomic():
        BakimKarariSnapshot.objects.create(**karar_degerleri(tahmin, **canonical))


def test_canonical_formul_surumu_bos_olamaz(tahmin):
    canonical = canonical_degerler()
    canonical["genel_oncelik_formul_surumu"] = ""
    with pytest.raises(IntegrityError), transaction.atomic():
        BakimKarariSnapshot.objects.create(**karar_degerleri(tahmin, **canonical))


def test_canonical_snapshot_sonradan_degistirilemez_ve_null_yapilamaz(tahmin):
    karar = BakimKarariSnapshot.objects.create(
        **karar_degerleri(tahmin, **canonical_degerler())
    )
    karar.genel_oncelik = 4
    with pytest.raises(ValueError):
        karar.save()
    with pytest.raises(ValueError):
        BakimKarariSnapshot.objects.filter(pk=karar.pk).update(genel_oncelik=None)


def test_legacy_snapshot_sonradan_canonical_hale_getirilemez(tahmin):
    karar = BakimKarariSnapshot.objects.create(**karar_degerleri(tahmin))
    canonical = canonical_degerler()
    for alan, deger in canonical.items():
        setattr(karar, alan, deger)
    with pytest.raises(ValueError):
        karar.save()
    with pytest.raises(ValueError):
        BakimKarariSnapshot.objects.filter(pk=karar.pk).update(**canonical)
