import math
from copy import deepcopy

DECISION_ENGINE_VERSION = "maintenance-priority-1.0.0"

TECHNICAL_WEIGHTS = {
    "risk_probability": 55.0,
    "machine_criticality": 25.0,
    "risk_warning": 10.0,
    "trusted_failure_type": 10.0,
    "uncertainty": 5.0,
    "experimental_twf": 2.0,
}
FINAL_WEIGHTS = {"technical": 0.8, "supply": 0.2}
PRIORITY_THRESHOLDS = ((75.0, "KRITIK"), (50.0, "YUKSEK"), (25.0, "ORTA"))
TRUSTED_FAILURE_TYPES = ("HDF", "PWF", "OSF")

ACTION_BY_LEVEL = {
    "DUSUK": "IZLEMEYE_DEVAM",
    "ORTA": "PLANLI_KONTROL",
    "YUKSEK": "ONCELIKLI_BAKIM_PLANLA",
    "KRITIK": "ACIL_TEKNIK_DEGERLENDIRME",
}

WARNING_TEMPLATES = {
    "SENTETIK_VERI_SINIRI": "Model sentetik veri bağlamındadır; otomatik durdurma kararı üretmez.",
    "INSAN_ONAYI_GEREKLI": "Nihai operasyonel karar yetkili bakım personeline aittir.",
}
REASON_TEMPLATES = {
    "MODEL_RISKI": "Model risk olasılığı teknik aciliyete katkı sağladı.",
    "MAKINE_KRITIKLIGI": "Makine kritiklik snapshot'ı teknik aciliyete katkı sağladı.",
    "RISK_ESIGI_ASILDI": "Binary risk eşiği aşıldı.",
    "GUVENILIR_FIZIKSEL_TIP": "Güvenilir fiziksel arıza tipi belirlendi.",
    "FIZIKSEL_TIP_BELIRSIZ": "Fiziksel arıza tipi güvenilir biçimde belirlenemedi.",
    "DENEYSEL_TWF_SINYALI": "TWF yalnız yetersiz destekli deneysel sinyal olarak değerlendirildi.",
    "STOK_YETERLI": "Gerekli parça stoğu snapshot anında yeterliydi.",
    "STOK_YETERSIZ": "Kullanılabilir stok gerekli miktarın altındaydı.",
    "STOK_KAYDI_YOK": "Stok kaydı bulunmadığı için ERP verisi doğrulanmalıdır.",
    "ERP_ESLESMESI_YOK": "İlgili arıza tipi için ERP parça eşlemesi bulunamadı.",
    "UZUN_TEDARIK": "Tedarik süresi bakım hazırlığını etkileyebilir.",
}


class KararMotoruGirdiHatasi(ValueError):
    pass


def _finite_number(value, name, *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise KararMotoruGirdiHatasi(f"{name} sayısal olmalıdır.")
    value = float(value)
    if not math.isfinite(value):
        raise KararMotoruGirdiHatasi(f"{name} sonlu olmalıdır.")
    if minimum is not None and value < minimum:
        raise KararMotoruGirdiHatasi(f"{name} alt sınırın dışındadır.")
    if maximum is not None and value > maximum:
        raise KararMotoruGirdiHatasi(f"{name} üst sınırın dışındadır.")
    return value


def _round_score(value):
    return round(max(0.0, min(100.0, value)), 2)


def priority_level(score):
    score = _finite_number(score, "nihai_oncelik_skoru", minimum=0, maximum=100)
    for threshold, level in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return level
    return "DUSUK"


def _reason(code, effect, points=None):
    return {
        "kod": code,
        "mesaj": REASON_TEMPLATES[code],
        "etki": effect,
        "puan_etkisi": None if points is None else round(points, 2),
    }


def _technical_score(data, trusted, twf_signal):
    risk = _finite_number(data["risk_orani"], "risk_orani", minimum=0, maximum=1)
    criticality = _finite_number(
        data["kritiklik_snapshot"], "kritiklik_snapshot", minimum=1, maximum=5
    )
    reasons = []
    risk_points = risk * TECHNICAL_WEIGHTS["risk_probability"]
    criticality_points = ((criticality - 1) / 4) * TECHNICAL_WEIGHTS[
        "machine_criticality"
    ]
    reasons.extend(
        (
            _reason("MODEL_RISKI", "ARTIRDI", risk_points),
            _reason("MAKINE_KRITIKLIGI", "ARTIRDI", criticality_points),
        )
    )
    score = risk_points + criticality_points
    if data["risk_uyarisi"]:
        score += TECHNICAL_WEIGHTS["risk_warning"]
        reasons.append(
            _reason("RISK_ESIGI_ASILDI", "ARTIRDI", TECHNICAL_WEIGHTS["risk_warning"])
        )
    if trusted:
        score += TECHNICAL_WEIGHTS["trusted_failure_type"]
        reasons.append(
            _reason(
                "GUVENILIR_FIZIKSEL_TIP",
                "ARTIRDI",
                TECHNICAL_WEIGHTS["trusted_failure_type"],
            )
        )
    elif data["risk_uyarisi"]:
        score += TECHNICAL_WEIGHTS["uncertainty"]
        reasons.append(
            _reason(
                "FIZIKSEL_TIP_BELIRSIZ", "ARTIRDI", TECHNICAL_WEIGHTS["uncertainty"]
            )
        )
    if twf_signal:
        score += TECHNICAL_WEIGHTS["experimental_twf"]
        reasons.append(
            _reason(
                "DENEYSEL_TWF_SINYALI", "ARTIRDI", TECHNICAL_WEIGHTS["experimental_twf"]
            )
        )
    if not data["risk_uyarisi"]:
        score = min(score, 39.0)
    return _round_score(score), reasons


def _part_supply_risk(part):
    code = str(part["parca_kodu_snapshot"])
    if part["stok_durumu"] == "KAYIT_YOK":
        return 55.0, code, "STOK_KAYDI_YOK"
    if part["stok_durumu"] != "MEVCUT":
        raise KararMotoruGirdiHatasi("stok_durumu geçersizdir.")
    available = _finite_number(
        part["kullanilabilir_stok"], "kullanilabilir_stok", minimum=0
    )
    required = _finite_number(part["gerekli_miktar"], "gerekli_miktar", minimum=1)
    minimum = _finite_number(part["minimum_stok"], "minimum_stok", minimum=0)
    lead_days = _finite_number(part["tedarik_gun"], "tedarik_gun", minimum=0)
    if available >= required:
        remaining = available - required
        return (20.0 if remaining < minimum else 5.0), code, "STOK_YETERLI"
    shortage_ratio = min(1.0, (required - available) / required)
    lead_risk = min(20.0, lead_days / 30.0 * 20.0)
    return (
        _round_score(60.0 + shortage_ratio * 20.0 + lead_risk),
        code,
        ("UZUN_TEDARIK" if lead_days >= 14 else "STOK_YETERSIZ"),
    )


def _supply_score(parts):
    if not parts:
        return 0.0, [_reason("ERP_ESLESMESI_YOK", "NOTR")], []
    evaluated = sorted(
        (_part_supply_risk(part) for part in parts), key=lambda x: (-x[0], x[1])
    )
    score, _, reason_code = evaluated[0]
    actions = []
    if any(item["stok_durumu"] == "KAYIT_YOK" for item in parts):
        actions.append("STOK_VERISINI_DOGRULA")
    if any(
        item["stok_durumu"] == "MEVCUT" and not item["stok_yeterli"] for item in parts
    ):
        actions.append("TEDARIK_SURECINI_BASLAT")
    return score, [_reason(reason_code, "ARTIRDI", score)], actions


def bakim_karari_hesapla(data):
    source = deepcopy(data)
    failures = list(source.get("ariza_tipleri", ()))
    if any(item.get("kod") == "RNF" for item in failures):
        raise KararMotoruGirdiHatasi("RNF karar motoru girdisi olamaz.")
    trusted = sorted(
        (
            item
            for item in failures
            if item.get("guvenilir_aday") and item.get("kod") in TRUSTED_FAILURE_TYPES
        ),
        key=lambda item: (item.get("siralama") or 999, item["kod"]),
    )
    twf_signal = any(
        item.get("kod") == "TWF"
        and item.get("esik_asildi")
        and not item.get("operasyonel_kullanima_uygun")
        for item in failures
    )
    technical, technical_reasons = _technical_score(source, trusted, twf_signal)
    operational_parts = [
        item
        for item in source.get("erp_snapshotlari", ())
        if not item.get("deneysel", False)
    ]
    supply, supply_reasons, supporting = _supply_score(
        sorted(operational_parts, key=lambda item: item["parca_kodu_snapshot"])
    )
    final = _round_score(
        technical * FINAL_WEIGHTS["technical"] + supply * FINAL_WEIGHTS["supply"]
    )
    level = priority_level(final)
    main_action = ACTION_BY_LEVEL[level]
    if source["risk_uyarisi"] and not trusted and level in {"DUSUK", "ORTA"}:
        main_action = "TEKNIK_INCELEME"
    missing_stock = any(
        part["stok_durumu"] == "KAYIT_YOK" for part in operational_parts
    )
    if source["risk_uyarisi"] and not trusted:
        confidence = "DUSUK" if twf_signal or missing_stock else "ORTA"
    elif trusted and operational_parts and not missing_stock:
        confidence = "YUKSEK"
    else:
        confidence = "ORTA"
    return {
        "motor_surumu": DECISION_ENGINE_VERSION,
        "teknik_aciliyet_skoru": technical,
        "tedarik_riski_skoru": supply,
        "nihai_oncelik_skoru": final,
        "oncelik_seviyesi": level,
        "ana_aksiyon": main_action,
        "destekleyici_aksiyonlar": supporting,
        "ana_ariza_tipi": trusted[0]["kod"] if trusted else None,
        "karar_guveni": confidence,
        "gerekceler": technical_reasons + supply_reasons,
        "uyarilar": [
            {"kod": code, "mesaj": message}
            for code, message in WARNING_TEMPLATES.items()
        ],
    }
