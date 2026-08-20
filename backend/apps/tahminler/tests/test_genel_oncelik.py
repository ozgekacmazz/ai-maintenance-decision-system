from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from apps.tahminler.genel_oncelik import (
    GENEL_ONCELIK_FORMUL_SURUMU,
    GenelOncelikGirdiHatasi,
    genel_oncelik_hesapla,
)


def hesapla(risk="0.5", kritiklik=4, tedarik="0"):
    return genel_oncelik_hesapla(
        risk_orani=risk,
        makine_kritikligi=kritiklik,
        tedarik_riski_skoru=tedarik,
    )


@pytest.mark.parametrize(
    ("tedarik", "beklenen"),
    [(0, "1.00"), (25, "1.25"), (55, "1.55"), (100, "2.00")],
)
def test_stok_katsayisi(tedarik, beklenen):
    assert hesapla(tedarik=tedarik).stok_katsayisi == Decimal(beklenen)


@pytest.mark.parametrize(
    ("hedef_ham", "beklenen_oncelik"),
    [
        ("0", 1),
        ("2", 1),
        ("2.00000001", 2),
        ("4", 2),
        ("4.00000001", 3),
        ("6", 3),
        ("6.00000001", 4),
        ("8", 4),
        ("8.00000001", 5),
        ("10", 5),
    ],
)
def test_kesin_esikler_tam_hassasiyetli_ham_sonuca_gore_belirlenir(
    hedef_ham, beklenen_oncelik
):
    # kritiklik=5 ve stok katsayısı=2 iken ham sonuç risk * 10'dur.
    risk = Decimal(hedef_ham) / Decimal("10")
    sonuc = hesapla(risk=risk, kritiklik=5, tedarik=100)
    assert sonuc.genel_oncelik == beklenen_oncelik


@pytest.mark.parametrize(
    ("risk", "kritiklik", "tedarik", "beklenen"),
    [
        ("0.1", 1, 0, 1),
        ("0.6", 5, 50, 3),
        ("1", 5, 100, 5),
        ("0", 5, 100, 1),
    ],
)
def test_temsili_senaryolar(risk, kritiklik, tedarik, beklenen):
    assert hesapla(risk, kritiklik, tedarik).genel_oncelik == beklenen


@pytest.mark.parametrize("alan", ["risk", "kritiklik", "tedarik"])
def test_girdiler_arttiginda_oncelik_azalmaz(alan):
    dusuk = {"risk": "0.4", "kritiklik": 3, "tedarik": 25}
    yuksek = dict(dusuk)
    yuksek[alan] = {"risk": "0.8", "kritiklik": 5, "tedarik": 100}[alan]
    assert hesapla(**dusuk).genel_oncelik <= hesapla(**yuksek).genel_oncelik


def test_float_girdi_decimal_str_yaklasimiyla_donusturulur():
    sonuc = hesapla(risk=0.1, kritiklik=5, tedarik=25.0)
    assert sonuc.risk_orani == Decimal("0.1")
    assert sonuc.stok_katsayisi == Decimal("1.25")
    assert sonuc.ham_genel_oncelik == Decimal("0.6250")


@pytest.mark.parametrize(
    ("ham", "beklenen"),
    [("1.99999999", 1), ("2", 1), ("2.00000001", 2)],
)
def test_quantization_esik_kararini_degistirmez(ham, beklenen):
    risk = Decimal(ham) / Decimal("10")
    sonuc = hesapla(risk=risk, kritiklik=5, tedarik=100)
    assert sonuc.ham_genel_oncelik == Decimal(ham).quantize(Decimal("0.0001"))
    assert sonuc.genel_oncelik == beklenen


@pytest.mark.parametrize(
    ("esik", "esik_onceligi", "ust_oncelik"),
    [("2", 1, 2), ("4", 2, 3), ("6", 3, 4), ("8", 4, 5)],
)
def test_her_esigin_hemen_alti_tami_ve_ustu_guvenlidir(
    esik, esik_onceligi, ust_oncelik
):
    esik_degeri = Decimal(esik)
    fark = Decimal("0.00000001")

    def esikten_hesapla(ham):
        return hesapla(risk=ham / Decimal("10"), kritiklik=5, tedarik=100)

    assert esikten_hesapla(esik_degeri - fark).genel_oncelik == esik_onceligi
    assert esikten_hesapla(esik_degeri).genel_oncelik == esik_onceligi
    assert esikten_hesapla(esik_degeri + fark).genel_oncelik == ust_oncelik


@pytest.mark.parametrize(
    ("alan", "deger"),
    [
        ("risk_orani", -1),
        ("risk_orani", "1.01"),
        ("makine_kritikligi", 0),
        ("makine_kritikligi", 6),
        ("makine_kritikligi", "2.5"),
        ("makine_kritikligi", True),
        ("tedarik_riski_skoru", -1),
        ("tedarik_riski_skoru", 101),
        ("risk_orani", Decimal("NaN")),
        ("risk_orani", Decimal("Infinity")),
        ("risk_orani", Decimal("-Infinity")),
        ("risk_orani", "sayi-degil"),
        ("risk_orani", None),
    ],
)
def test_gecersiz_girdiler_reddedilir(alan, deger):
    girdiler = {
        "risk_orani": "0.5",
        "makine_kritikligi": 3,
        "tedarik_riski_skoru": 50,
    }
    girdiler[alan] = deger
    with pytest.raises(GenelOncelikGirdiHatasi, match=alan):
        genel_oncelik_hesapla(**girdiler)


def test_sonuc_deterministik_immutable_ve_surumludur():
    ilk = hesapla()
    assert ilk == hesapla()
    assert ilk.formul_surumu == GENEL_ONCELIK_FORMUL_SURUMU
    with pytest.raises(FrozenInstanceError):
        ilk.genel_oncelik = 5
