from copy import deepcopy

import pytest

from apps.tahminler.decision_engine import (
    FINAL_WEIGHTS,
    KararMotoruGirdiHatasi,
    bakim_karari_hesapla,
    priority_level,
)


def input_data(**overrides):
    data = {
        "risk_orani": 0.8,
        "risk_uyarisi": True,
        "kritiklik_snapshot": 5,
        "belirsiz_fiziksel_tip": False,
        "ariza_tipleri": [
            {
                "kod": "HDF",
                "esik_asildi": True,
                "operasyonel_kullanima_uygun": True,
                "guvenilir_aday": True,
                "siralama": 1,
            }
        ],
        "erp_snapshotlari": [
            {
                "parca_kodu_snapshot": "P-1",
                "gerekli_miktar": 1,
                "stok_durumu": "MEVCUT",
                "kullanilabilir_stok": 2,
                "minimum_stok": 1,
                "tedarik_gun": 3,
                "stok_yeterli": True,
                "deneysel": False,
            }
        ],
    }
    data.update(overrides)
    return data


def test_same_input_produces_same_output_without_mutation():
    data = input_data()
    original = deepcopy(data)
    assert bakim_karari_hesapla(data) == bakim_karari_hesapla(data)
    assert data == original


def test_input_list_order_does_not_change_decision():
    parts = [
        input_data()["erp_snapshotlari"][0],
        {
            "parca_kodu_snapshot": "P-2",
            "gerekli_miktar": 2,
            "stok_durumu": "MEVCUT",
            "kullanilabilir_stok": 0,
            "minimum_stok": 1,
            "tedarik_gun": 30,
            "stok_yeterli": False,
            "deneysel": False,
        },
    ]
    first = bakim_karari_hesapla(input_data(erp_snapshotlari=parts))
    second = bakim_karari_hesapla(input_data(erp_snapshotlari=list(reversed(parts))))
    assert first == second
    assert first["tedarik_riski_skoru"] == 100


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_values_are_rejected(value):
    with pytest.raises(KararMotoruGirdiHatasi):
        bakim_karari_hesapla(input_data(risk_orani=value))


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "DUSUK"),
        (24.99, "DUSUK"),
        (25, "ORTA"),
        (49.99, "ORTA"),
        (50, "YUKSEK"),
        (74.99, "YUKSEK"),
        (75, "KRITIK"),
        (100, "KRITIK"),
    ],
)
def test_priority_boundaries(score, expected):
    assert priority_level(score) == expected


def test_all_scores_are_clamped_to_zero_and_one_hundred():
    result = bakim_karari_hesapla(input_data())
    assert all(
        0 <= result[field] <= 100
        for field in (
            "teknik_aciliyet_skoru",
            "tedarik_riski_skoru",
            "nihai_oncelik_skoru",
        )
    )
    assert sum(FINAL_WEIGHTS.values()) == 1


def test_low_risk_never_becomes_critical_without_erp_context():
    result = bakim_karari_hesapla(
        input_data(
            risk_orani=0.2,
            risk_uyarisi=False,
            ariza_tipleri=[],
            erp_snapshotlari=[],
        )
    )
    assert result["oncelik_seviyesi"] != "KRITIK"
    assert result["ana_aksiyon"] in {"IZLEMEYE_DEVAM", "PLANLI_KONTROL"}


def test_high_risk_critical_machine_remains_high_with_stock_available():
    result = bakim_karari_hesapla(input_data(risk_orani=1.0))
    assert result["teknik_aciliyet_skoru"] >= 90
    assert result["nihai_oncelik_skoru"] >= 75
    assert result["ana_ariza_tipi"] == "HDF"
    assert result["karar_guveni"] == "YUKSEK"


def test_uncertain_physical_type_requires_technical_review_reason():
    result = bakim_karari_hesapla(
        input_data(ariza_tipleri=[], erp_snapshotlari=[], belirsiz_fiziksel_tip=True)
    )
    assert result["ana_ariza_tipi"] is None
    assert "FIZIKSEL_TIP_BELIRSIZ" in {item["kod"] for item in result["gerekceler"]}
    assert result["karar_guveni"] == "ORTA"


def test_twf_is_experimental_only_and_does_not_drive_supply_decision():
    twf = {
        "kod": "TWF",
        "esik_asildi": True,
        "operasyonel_kullanima_uygun": False,
        "guvenilir_aday": False,
        "siralama": None,
    }
    experimental_part = {
        **input_data()["erp_snapshotlari"][0],
        "stok_durumu": "KAYIT_YOK",
        "kullanilabilir_stok": None,
        "minimum_stok": None,
        "tedarik_gun": None,
        "stok_yeterli": False,
        "deneysel": True,
    }
    result = bakim_karari_hesapla(
        input_data(ariza_tipleri=[twf], erp_snapshotlari=[experimental_part])
    )
    assert result["ana_ariza_tipi"] is None
    assert result["tedarik_riski_skoru"] == 0
    assert result["karar_guveni"] == "DUSUK"


def test_rnf_is_rejected_and_never_appears_in_output():
    rnf = {"kod": "RNF", "guvenilir_aday": True}
    with pytest.raises(KararMotoruGirdiHatasi):
        bakim_karari_hesapla(input_data(ariza_tipleri=[rnf]))


def test_zero_stock_and_long_lead_time_are_a_supply_bottleneck():
    part = {
        **input_data()["erp_snapshotlari"][0],
        "kullanilabilir_stok": 0,
        "stok_yeterli": False,
        "tedarik_gun": 30,
    }
    result = bakim_karari_hesapla(input_data(erp_snapshotlari=[part]))
    assert result["tedarik_riski_skoru"] == 100
    assert "TEDARIK_SURECINI_BASLAT" in result["destekleyici_aksiyonlar"]


def test_missing_stock_record_is_not_treated_as_zero_stock():
    part = {
        **input_data()["erp_snapshotlari"][0],
        "stok_durumu": "KAYIT_YOK",
        "kullanilabilir_stok": None,
        "minimum_stok": None,
        "tedarik_gun": None,
        "stok_yeterli": False,
    }
    result = bakim_karari_hesapla(input_data(erp_snapshotlari=[part]))
    assert result["tedarik_riski_skoru"] == 55
    assert result["destekleyici_aksiyonlar"] == ["STOK_VERISINI_DOGRULA"]
    assert result["karar_guveni"] != "YUKSEK"


def test_no_erp_mapping_is_neutral_for_supply_score():
    result = bakim_karari_hesapla(input_data(erp_snapshotlari=[]))
    assert result["tedarik_riski_skoru"] == 0
    assert result["gerekceler"][-1]["kod"] == "ERP_ESLESMESI_YOK"


def test_reason_points_and_order_are_deterministic():
    result = bakim_karari_hesapla(input_data())
    technical_points = sum(
        reason["puan_etkisi"]
        for reason in result["gerekceler"]
        if reason["kod"]
        in {
            "MODEL_RISKI",
            "MAKINE_KRITIKLIGI",
            "RISK_ESIGI_ASILDI",
            "GUVENILIR_FIZIKSEL_TIP",
        }
    )
    assert technical_points == result["teknik_aciliyet_skoru"]
    assert [item["kod"] for item in result["uyarilar"]] == [
        "SENTETIK_VERI_SINIRI",
        "INSAN_ONAYI_GEREKLI",
    ]
