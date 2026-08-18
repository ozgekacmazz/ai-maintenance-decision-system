import math
import threading

import numpy as np
from bakim_ml.explainability import (
    ExplainabilityError,
    create_tree_explainer,
    explain_prepared_pipeline,
)

from apps.tahminler.exceptions import ModelHizmetiHatasi

FEATURE_PRESENTATION = {
    "hava_sicakligi_k": ("Hava sıcaklığı", "K"),
    "proses_sicakligi_k": ("Proses sıcaklığı", "K"),
    "donus_hizi_rpm": ("Dönüş hızı", "rpm"),
    "tork_nm": ("Tork", "Nm"),
    "takim_asinmasi_dk": ("Takım aşınması", "dakika"),
    "proses_hava_sicaklik_farki_k": ("Proses–hava sıcaklık farkı", "K"),
    "acisal_hiz_rad_s": ("Açısal hız", "rad/s"),
    "mekanik_guc_w": ("Mekanik güç", "W"),
    "urun_tipi_H": ("Ürün tipi H", None),
    "urun_tipi_L": ("Ürün tipi L", None),
    "urun_tipi_M": ("Ürün tipi M", None),
}

_binary_lock = threading.Lock()
_failure_type_lock = threading.Lock()
_binary_cache = None
_failure_type_cache = {}


def binary_explainer_cache_sifirla():
    global _binary_cache
    with _binary_lock:
        _binary_cache = None


def ariza_tipi_explainer_cache_sifirla(label=None):
    with _failure_type_lock:
        if label is None:
            _failure_type_cache.clear()
        else:
            _failure_type_cache.pop(label, None)


def explainer_cache_sifirla():
    binary_explainer_cache_sifirla()
    ariza_tipi_explainer_cache_sifirla()


def binary_explainer_getir(pipeline):
    global _binary_cache
    cached = _binary_cache
    if cached is not None and cached[0] is pipeline:
        return cached[1]
    with _binary_lock:
        if _binary_cache is None or _binary_cache[0] is not pipeline:
            created = create_tree_explainer(pipeline)
            _binary_cache = (pipeline, created)
        return _binary_cache[1]


def ariza_tipi_explainer_getir(label, pipeline):
    cached = _failure_type_cache.get(label)
    if cached is not None and cached[0] is pipeline:
        return cached[1]
    with _failure_type_lock:
        cached = _failure_type_cache.get(label)
        if cached is None or cached[0] is not pipeline:
            created = create_tree_explainer(pipeline)
            _failure_type_cache[label] = (pipeline, created)
        return _failure_type_cache[label][1]


def _original_value(feature, prepared_features):
    if feature.startswith("urun_tipi_"):
        category = feature.removeprefix("urun_tipi_")
        return bool(prepared_features.iloc[0]["urun_tipi"] == category)
    if feature not in prepared_features.columns:
        raise ExplainabilityError("Bilinmeyen transformed feature.")
    value = float(prepared_features.iloc[0][feature])
    if not math.isfinite(value):
        raise ExplainabilityError("Original feature değeri sonlu değil.")
    return value


def _sunuma_cevir(explanation, prepared_features):
    effects = []
    for contribution in explanation["feature_contributions"]:
        feature = contribution["feature"]
        if feature not in FEATURE_PRESENTATION:
            raise ExplainabilityError("Bilinmeyen transformed feature.")
        display_name, unit = FEATURE_PRESENTATION[feature]
        model_value = float(contribution["feature_value"])
        shap_value = float(contribution["shap_value"])
        if not np.isfinite((model_value, shap_value)).all():
            raise ExplainabilityError("Açıklama değeri sonlu değil.")
        effects.append(
            {
                "feature": feature,
                "gorunen_ad": display_name,
                "original_feature_value": _original_value(feature, prepared_features),
                "model_feature_value": model_value,
                "birim": unit,
                "shap_value": shap_value,
                "yon": contribution["direction"],
            }
        )
    return {
        "target": explanation["target"],
        "output_space": explanation["output_space"],
        "base_value": explanation["base_value"],
        "ilk_etkiler": effects,
    }


def aciklama_uret(
    pipeline,
    prepared_features,
    *,
    target,
    probability,
    top_n,
    label=None,
):
    try:
        explainer = (
            binary_explainer_getir(pipeline)
            if label is None
            else ariza_tipi_explainer_getir(label, pipeline)
        )
        explanation = explain_prepared_pipeline(
            pipeline,
            prepared_features,
            explainer=explainer,
            target=target,
            top_n=top_n,
            predicted_probability=probability,
        )
        return _sunuma_cevir(explanation, prepared_features)
    except ModelHizmetiHatasi:
        raise
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
