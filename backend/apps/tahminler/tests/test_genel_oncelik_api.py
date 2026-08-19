from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bakim.models import Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.models import BakimKarariSnapshot, TahminKaydi

pytestmark = pytest.mark.django_db

URL = "/api/tahminler/kayitlar/"


@pytest.fixture
def client_and_user():
    user = Kullanici.objects.create_user(username="b4-user", password="unused")
    client = APIClient()
    client.force_authenticate(user)
    return client, user


@pytest.fixture
def makine():
    return Makine.objects.create(
        makine_kodu="M-B4", ad="B4 Makinesi", tip="Test", kritiklik=5
    )


def kayit_olustur(
    user,
    makine,
    *,
    key,
    risk,
    nihai_skor,
    genel_oncelik=None,
    olcum_farki=0,
):
    record = TahminKaydi.objects.create(
        makine=makine,
        olusturan=user,
        trace_id=f"trace-{key}",
        kaynak="MANUEL",
        olcum_zamani=timezone.now() + timedelta(minutes=olcum_farki),
        idempotency_key=key,
        payload_fingerprint=key.ljust(64, "a")[:64],
        makine_kodu_snapshot=makine.makine_kodu,
        makine_adi_snapshot=makine.ad,
        kritiklik_snapshot=makine.kritiklik,
        sensor_snapshot={},
        risk_orani=risk,
        risk_uyarisi=True,
        binary_threshold=0.2,
        binary_model_version="binary-v",
        binary_pipeline_version="pipeline-v",
        failure_type_durum="DEGERLENDIRILDI",
        belirsiz_fiziksel_tip=False,
        aciklanabilirlik_durum="ACIKLANDI",
    )
    canonical = {}
    if genel_oncelik is not None:
        canonical = {
            "genel_oncelik": genel_oncelik,
            "stok_katsayisi": Decimal("1.55"),
            "ham_genel_oncelik": Decimal("4.6500"),
            "genel_oncelik_formul_surumu": "general-priority-1.0.0",
        }
    BakimKarariSnapshot.objects.create(
        tahmin=record,
        motor_surumu="maintenance-priority-1.0.0",
        teknik_aciliyet_skoru=50,
        tedarik_riski_skoru=55,
        nihai_oncelik_skoru=nihai_skor,
        oncelik_seviyesi="YUKSEK",
        ana_aksiyon="ONCELIKLI_BAKIM_PLANLA",
        karar_guveni="YUKSEK",
        **canonical,
    )
    return record


def test_canonical_ve_legacy_detay_sozlesmesi(client_and_user, makine):
    client, user = client_and_user
    canonical = kayit_olustur(
        user,
        makine,
        key="canonical-detail",
        risk=0.6,
        nihai_skor=58.4,
        genel_oncelik=3,
    )
    legacy = kayit_olustur(user, makine, key="legacy-detail", risk=0.4, nihai_skor=42)

    canonical_data = client.get(f"{URL}{canonical.pk}/").data["bakim_karari"]
    legacy_data = client.get(f"{URL}{legacy.pk}/").data["bakim_karari"]

    assert canonical_data["genel_oncelik"] == 3
    assert canonical_data["stok_katsayisi"] == "1.55"
    assert canonical_data["ham_genel_oncelik"] == "4.6500"
    assert canonical_data["genel_oncelik_formul_surumu"] == "general-priority-1.0.0"
    assert canonical_data["nihai_oncelik_skoru"] == 58.4
    assert legacy_data["genel_oncelik"] is None
    assert legacy_data["stok_katsayisi"] is None
    assert legacy_data["ham_genel_oncelik"] is None
    assert legacy_data["genel_oncelik_formul_surumu"] is None
    assert legacy_data["nihai_oncelik_skoru"] == 42


def test_liste_canonical_ve_legacy_kayitlari_birlikte_serilestirir(
    client_and_user, makine
):
    client, user = client_and_user
    kayit_olustur(
        user, makine, key="canonical-list", risk=0.6, nihai_skor=58, genel_oncelik=3
    )
    kayit_olustur(user, makine, key="legacy-list", risk=0.4, nihai_skor=42)

    results = client.get(URL).data["results"]
    by_trace = {item["trace_id"]: item for item in results}

    assert by_trace["trace-canonical-list"]["genel_oncelik"] == 3
    assert (
        by_trace["trace-canonical-list"]["genel_oncelik_formul_surumu"]
        == "general-priority-1.0.0"
    )
    assert by_trace["trace-legacy-list"]["genel_oncelik"] is None
    assert by_trace["trace-legacy-list"]["genel_oncelik_formul_surumu"] is None


def test_genel_oncelik_filtresi_legacy_null_kaydi_dislar_ve_kaynakla_birlesir(
    client_and_user, makine
):
    client, user = client_and_user
    expected = kayit_olustur(
        user, makine, key="filter-3", risk=0.6, nihai_skor=58, genel_oncelik=3
    )
    kayit_olustur(
        user, makine, key="filter-5", risk=0.9, nihai_skor=90, genel_oncelik=5
    )
    kayit_olustur(user, makine, key="filter-legacy", risk=0.4, nihai_skor=42)

    response = client.get(URL, {"genel_oncelik": 3, "kaynak": "MANUEL"})

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(expected.pk)]


@pytest.mark.parametrize("value", ["0", "6", "-1", "1.5", "", "metin"])
def test_gecersiz_genel_oncelik_filtresi_standart_400_dondurur(client_and_user, value):
    client, _ = client_and_user
    response = client.get(URL, {"genel_oncelik": value}, HTTP_X_TRACE_ID="b4-trace")

    assert response.status_code == 400
    assert response.data["hata"]["kod"] == "GECERSIZ_ISTEK"
    assert response.data["hata"]["alanlar"]["genel_oncelik"]
    assert response.data["hata"]["trace_id"] == "b4-trace"


@pytest.mark.parametrize(
    ("sirala", "beklenen"),
    [
        ("-genel_oncelik", ["priority-5", "priority-3", "priority-1", "legacy"]),
        ("genel_oncelik", ["priority-1", "priority-3", "priority-5", "legacy"]),
    ],
)
def test_canonical_siralama_iki_yonde_nullari_sona_atir(
    client_and_user, makine, sirala, beklenen
):
    client, user = client_and_user
    for key, priority in (("priority-1", 1), ("priority-3", 3), ("priority-5", 5)):
        kayit_olustur(
            user,
            makine,
            key=key,
            risk=priority / 10,
            nihai_skor=priority * 10,
            genel_oncelik=priority,
        )
    kayit_olustur(user, makine, key="legacy", risk=0.9, nihai_skor=99)

    results = client.get(URL, {"sirala": sirala}).data["results"]

    assert [item["trace_id"].removeprefix("trace-") for item in results] == beklenen


def test_canonical_siralama_esitlikte_riski_azalan_kullanir(client_and_user, makine):
    client, user = client_and_user
    kayit_olustur(
        user, makine, key="low-risk", risk=0.2, nihai_skor=50, genel_oncelik=3
    )
    kayit_olustur(
        user, makine, key="high-risk", risk=0.8, nihai_skor=50, genel_oncelik=3
    )

    results = client.get(URL, {"sirala": "genel_oncelik"}).data["results"]

    assert [item["trace_id"] for item in results] == [
        "trace-high-risk",
        "trace-low-risk",
    ]


def test_default_ordering_legacy_nihai_skor_sozlesmesini_korur(client_and_user, makine):
    client, user = client_and_user
    kayit_olustur(
        user, makine, key="canonical-1", risk=0.2, nihai_skor=90, genel_oncelik=1
    )
    kayit_olustur(
        user, makine, key="canonical-5", risk=0.9, nihai_skor=10, genel_oncelik=5
    )

    results = client.get(URL).data["results"]

    assert [item["trace_id"] for item in results] == [
        "trace-canonical-1",
        "trace-canonical-5",
    ]
