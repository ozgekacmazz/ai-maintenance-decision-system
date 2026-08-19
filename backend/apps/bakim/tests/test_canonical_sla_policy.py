from datetime import datetime, timedelta, timezone

import pytest

from apps.bakim.work_order_policy import (
    GENEL_ONCELIK_SLA_POLITIKASI_SURUMU,
    IsEmriPolitikaHatasi,
    genel_oncelik_hedef_mudahale_zamani,
    hedef_mudahale_zamani,
)


@pytest.mark.parametrize(
    ("genel_oncelik", "saat"),
    [(5, 4), (4, 24), (3, 72), (2, 120), (1, 168)],
)
def test_genel_oncelik_sla_tablosu(genel_oncelik, saat):
    baslangic = datetime(2026, 8, 19, 10, 30, tzinfo=timezone.utc)

    sonuc = genel_oncelik_hedef_mudahale_zamani(
        baslangic=baslangic, genel_oncelik=genel_oncelik
    )

    assert sonuc == baslangic + timedelta(hours=saat)
    assert sonuc.tzinfo is baslangic.tzinfo


def test_genel_oncelik_sla_surumu_sabittir():
    assert GENEL_ONCELIK_SLA_POLITIKASI_SURUMU == "general-priority-sla-1.0.0"


@pytest.mark.parametrize("gecersiz", [True, False, 0, 6, -1, 1.5, "3", None])
def test_genel_oncelik_sla_gecersiz_degeri_reddeder(gecersiz):
    with pytest.raises(IsEmriPolitikaHatasi, match="1 ile 5 arasında bir tam sayı"):
        genel_oncelik_hedef_mudahale_zamani(
            baslangic=datetime(2026, 8, 19), genel_oncelik=gecersiz
        )


@pytest.mark.parametrize(
    ("legacy_oncelik", "saat"),
    [("KRITIK", 4), ("YUKSEK", 24), ("ORTA", 72), ("DUSUK", 168)],
)
def test_legacy_sla_davranisi_degismedi(legacy_oncelik, saat):
    baslangic = datetime(2026, 8, 19, 10, 30)

    assert hedef_mudahale_zamani(
        baslangic=baslangic, oncelik=legacy_oncelik
    ) == baslangic + timedelta(hours=saat)
