import math

from rest_framework.exceptions import ValidationError

from apps.tahminler.input_domain import input_domain_contract_getir


def _aralik_metni(alan, alt, ust, birim):
    if alan in {"hava_sicakligi_k", "proses_sicakligi_k"}:
        return f"{alt:g}–{ust:g} K (yaklaşık {alt - 273.15:.1f}–{ust - 273.15:.1f} °C)"
    return f"{alt:g}–{ust:g} {birim}"


def model_girdilerini_dogrula(veriler: dict) -> dict:
    """Kanonik Kelvin girdilerini sürümlü model-domain sözleşmesine göre doğrular."""
    contract = input_domain_contract_getir()
    features = contract["features"]
    hatalar = {}
    urun_tipi = veriler.get("urun_tipi")
    allowed = features["urun_tipi"]["allowed"]
    if urun_tipi not in allowed:
        hatalar["urun_tipi"] = [
            f"Geçersiz ürün tipi '{urun_tipi}'. Geçerli değerler: {', '.join(allowed)}."
        ]

    for alan in (
        "hava_sicakligi_k",
        "proses_sicakligi_k",
        "donus_hizi_rpm",
        "tork_nm",
        "takim_asinmasi_dk",
    ):
        deger = veriler.get(alan)
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            hatalar[alan] = ["Geçerli bir sayı girilmelidir."]
            continue
        if not math.isfinite(deger):
            hatalar[alan] = ["Sayısal değer NaN veya Infinity olamaz."]
            continue
        cfg = features[alan]
        if not cfg["physical_min"] <= deger <= cfg["physical_max"]:
            aralik = _aralik_metni(
                alan, cfg["physical_min"], cfg["physical_max"], cfg["unit"]
            )
            hatalar[alan] = [f"Girilen değer fiziksel sınırlar dışında ({aralik})."]
        elif not cfg["supported_min"] <= deger <= cfg["supported_max"]:
            aralik = _aralik_metni(
                alan, cfg["supported_min"], cfg["supported_max"], cfg["unit"]
            )
            hatalar[alan] = [
                f"Değer modelin desteklediği çalışma aralığının dışında ({aralik}). Birimi ve sensör değerini kontrol edin."
            ]
    if hatalar:
        raise ValidationError(hatalar)

    sicaklik_farki = float(veriler["proses_sicakligi_k"]) - float(
        veriler["hava_sicakligi_k"]
    )
    fark_siniri = features["proses_hava_sicaklik_farki_k"]
    if (
        not fark_siniri["supported_min"]
        <= sicaklik_farki
        <= fark_siniri["supported_max"]
    ):
        hatalar["proses_sicakligi_k"] = [
            f"Proses ve hava sıcaklığı farkı ({sicaklik_farki:.1f} K) model domain'i dışında ({fark_siniri['supported_min']:g}–{fark_siniri['supported_max']:g} K)."
        ]
    mekanik_guc = (
        float(veriler["tork_nm"])
        * float(veriler["donus_hizi_rpm"])
        * (2.0 * math.pi / 60.0)
    )
    guc_siniri = features["mekanik_guc_w"]
    if not guc_siniri["supported_min"] <= mekanik_guc <= guc_siniri["supported_max"]:
        hatalar["tork_nm"] = [
            f"Tork ve dönüş hızından hesaplanan mekanik güç ({mekanik_guc:.1f} W) model domain'i dışında ({guc_siniri['supported_min']:g}–{guc_siniri['supported_max']:g} W)."
        ]
    if hatalar:
        raise ValidationError(hatalar)
    return veriler
