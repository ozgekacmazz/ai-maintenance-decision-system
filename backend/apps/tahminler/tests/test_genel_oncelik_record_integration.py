from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

from apps.bakim.models import Makine
from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import KararMotoruHatasi
from apps.tahminler.genel_oncelik import (
    GENEL_ONCELIK_FORMUL_SURUMU,
    GenelOncelikGirdiHatasi,
    genel_oncelik_hesapla,
)
from apps.tahminler.models import BakimKarariSnapshot, TahminKaydi
from apps.tahminler.record_services import (
    payload_fingerprint,
    tahmin_kaydi_olustur,
)

pytestmark = pytest.mark.django_db

SENSOR = {
    "urun_tipi": "L",
    "hava_sicakligi_k": 298.1,
    "proses_sicakligi_k": 308.6,
    "donus_hizi_rpm": 1551,
    "tork_nm": 42.8,
    "takim_asinmasi_dk": 0,
}
OLCUM_ZAMANI = datetime(2026, 8, 19, 12, tzinfo=timezone.utc)


@pytest.fixture
def kullanici():
    return Kullanici.objects.create_user(username="b3-user", password="unused")


@pytest.fixture
def makine():
    return Makine.objects.create(
        makine_kodu="M-B3", ad="B3 Makinesi", tip="Test", kritiklik=5
    )


def inference_result():
    return {
        "risk_orani": 0.6,
        "risk_uyarisi": True,
        "threshold": 0.2,
        "model_version": "binary-1",
        "pipeline_version": "pipeline-1",
        "ariza_tipi_degerlendirmesi": {
            "durum": "DEGERLENDIRILDI",
            "model_version": "failure-1",
            "pipeline_version": "pipeline-1",
            "guvenilir_adaylar": [],
            "deneysel_sinyaller": [],
            "belirsiz_fiziksel_tip": True,
        },
        "aciklanabilirlik": {
            "durum": "ACIKLANDI",
            "risk_aciklamasi": None,
        },
    }


def veriler(makine, *, kaynak="MANUEL", key="b3-key"):
    return {
        "makine_id": makine.pk,
        "olcum_zamani": OLCUM_ZAMANI,
        "kaynak": kaynak,
        "idempotency_key": key,
        "sensor_verisi": SENSOR,
    }


def servis_cagrisi(kullanici, makine, *, kaynak="MANUEL", key="b3-key"):
    with (
        patch(
            "apps.tahminler.record_services._ozellikleri_hazirla",
            return_value=pd.DataFrame([{}]),
        ),
        patch(
            "apps.tahminler.record_services.hiyerarsik_risk_tahmini_yap",
            return_value=inference_result(),
        ),
    ):
        return tahmin_kaydi_olustur(
            kullanici=kullanici,
            trace_id="b3-trace",
            veriler=veriler(makine, kaynak=kaynak, key=key),
        )


@pytest.mark.parametrize("kaynak", ["MANUEL", "ENTEGRASYON", "REPLAY"])
def test_tum_uretim_kaynaklari_ayni_servisten_canonical_snapshot_alir(
    kullanici, makine, kaynak
):
    tahmin, tekrarlandi = servis_cagrisi(
        kullanici, makine, kaynak=kaynak, key=f"b3-{kaynak.lower()}"
    )
    karar = tahmin.bakim_karari
    beklenen = genel_oncelik_hesapla(
        risk_orani=tahmin.risk_orani,
        makine_kritikligi=tahmin.kritiklik_snapshot,
        tedarik_riski_skoru=karar.tedarik_riski_skoru,
    )

    assert tekrarlandi is False
    assert karar.genel_oncelik == beklenen.genel_oncelik == 2
    assert karar.stok_katsayisi == beklenen.stok_katsayisi == Decimal("1.00")
    assert karar.ham_genel_oncelik == beklenen.ham_genel_oncelik == Decimal("3.0000")
    assert (
        karar.genel_oncelik_formul_surumu
        == beklenen.formul_surumu
        == GENEL_ONCELIK_FORMUL_SURUMU
    )
    assert karar.motor_surumu == "maintenance-priority-1.0.0"
    assert karar.teknik_aciliyet_skoru == 73
    assert karar.tedarik_riski_skoru == 0
    assert karar.nihai_oncelik_skoru == 58.4
    assert karar.oncelik_seviyesi == "YUKSEK"


def test_idempotent_tekrar_canonical_hesabi_ve_snapshoti_tekrarlamaz(kullanici, makine):
    with patch(
        "apps.tahminler.record_services.genel_oncelik_hesapla",
        wraps=genel_oncelik_hesapla,
    ) as hesaplayici:
        ilk, ilk_tekrar = servis_cagrisi(kullanici, makine)
        ilk_degerler = (
            ilk.bakim_karari.genel_oncelik,
            ilk.bakim_karari.stok_katsayisi,
            ilk.bakim_karari.ham_genel_oncelik,
            ilk.bakim_karari.genel_oncelik_formul_surumu,
        )
        ikinci, ikinci_tekrar = servis_cagrisi(kullanici, makine)

    assert ilk_tekrar is False
    assert ikinci_tekrar is True
    assert ikinci.pk == ilk.pk
    assert BakimKarariSnapshot.objects.filter(tahmin=ilk).count() == 1
    assert hesaplayici.call_count == 1
    assert (
        ikinci.bakim_karari.genel_oncelik,
        ikinci.bakim_karari.stok_katsayisi,
        ikinci.bakim_karari.ham_genel_oncelik,
        ikinci.bakim_karari.genel_oncelik_formul_surumu,
    ) == ilk_degerler


def test_existing_legacy_snapshot_idempotent_tekrarda_backfill_edilmez(
    kullanici, makine
):
    request = veriler(makine)
    fingerprint = payload_fingerprint(
        makine_id=makine.pk,
        olcum_zamani=OLCUM_ZAMANI,
        kaynak="MANUEL",
        sensor_verisi=SENSOR,
    )
    tahmin = TahminKaydi.objects.create(
        makine=makine,
        olusturan=kullanici,
        trace_id="legacy",
        kaynak="MANUEL",
        olcum_zamani=OLCUM_ZAMANI,
        idempotency_key="b3-key",
        payload_fingerprint=fingerprint,
        makine_kodu_snapshot=makine.makine_kodu,
        makine_adi_snapshot=makine.ad,
        kritiklik_snapshot=makine.kritiklik,
        sensor_snapshot=SENSOR,
        risk_orani=0.6,
        risk_uyarisi=True,
        binary_threshold=0.2,
        binary_model_version="binary-1",
        binary_pipeline_version="pipeline-1",
        failure_type_durum="DEGERLENDIRILDI",
        belirsiz_fiziksel_tip=True,
        aciklanabilirlik_durum="ACIKLANDI",
    )
    karar = BakimKarariSnapshot.objects.create(
        tahmin=tahmin,
        motor_surumu="maintenance-priority-1.0.0",
        teknik_aciliyet_skoru=73,
        tedarik_riski_skoru=0,
        nihai_oncelik_skoru=58.4,
        oncelik_seviyesi="YUKSEK",
        ana_aksiyon="ONCELIKLI_BAKIM_PLANLA",
        karar_guveni="ORTA",
    )

    with patch("apps.tahminler.record_services.genel_oncelik_hesapla") as hesaplayici:
        mevcut, tekrarlandi = tahmin_kaydi_olustur(
            kullanici=kullanici,
            trace_id="repeat",
            veriler=request,
        )

    karar.refresh_from_db()
    assert tekrarlandi is True
    assert mevcut.pk == tahmin.pk
    assert BakimKarariSnapshot.objects.filter(tahmin=tahmin).count() == 1
    assert hesaplayici.call_count == 0
    assert karar.genel_oncelik is None
    assert karar.stok_katsayisi is None
    assert karar.ham_genel_oncelik is None
    assert karar.genel_oncelik_formul_surumu is None


def test_canonical_hesap_hatasi_tum_tahmin_transactionini_geri_alir(kullanici, makine):
    with patch(
        "apps.tahminler.record_services.genel_oncelik_hesapla",
        side_effect=GenelOncelikGirdiHatasi("gecersiz canonical girdi"),
    ):
        with pytest.raises(KararMotoruHatasi):
            servis_cagrisi(kullanici, makine)

    assert TahminKaydi.objects.count() == 0
    assert BakimKarariSnapshot.objects.count() == 0
