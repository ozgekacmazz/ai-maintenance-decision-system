import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from bakim_ml.artifact import load_trusted_artifact, load_trusted_failure_type_artifact
from bakim_ml.data_contract import (
    MODEL_FEATURE_COLUMNS,
    MODELED_FAILURE_TYPE_COLUMNS,
    PIPELINE_VERSION,
)
from bakim_ml.features import add_engineered_features
from bakim_ml.modeling import feature_frame
from django.conf import settings

from apps.tahminler.domain_validation import model_girdilerini_dogrula
from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.explainability import (
    aciklama_uret,
    ariza_tipi_explainer_cache_sifirla,
    binary_explainer_cache_sifirla,
)
from apps.tahminler.input_domain import input_domain_contract_getir
from apps.tahminler.policy import (
    DENEYSEL_FIZIKSEL_TIPLER,
    GUVENILIR_FIZIKSEL_TIPLER,
    YETERSIZ_DESTEK,
)

MODEL_VERSION = "binary-failure-1.0.0"
FAILURE_TYPE_MODEL_VERSION = "failure-type-1.0.0"
_binary_cache_lock = threading.Lock()
_failure_type_cache_lock = threading.Lock()
_cached_model = None
_cached_paths = None
_cached_failure_type_model = None
_cached_failure_type_paths = None


@dataclass(frozen=True)
class YukluModel:
    pipeline: object
    threshold: float
    model_version: str
    pipeline_version: str


@dataclass(frozen=True)
class YukluArizaTipiModeli:
    pipelines: dict
    thresholds: dict
    model_version: str
    pipeline_version: str


def model_cache_sifirla():
    binary_model_cache_sifirla()
    ariza_tipi_model_cache_sifirla()


def binary_model_cache_sifirla():
    global _cached_model, _cached_paths
    with _binary_cache_lock:
        _cached_model = None
        _cached_paths = None
    binary_explainer_cache_sifirla()


def ariza_tipi_model_cache_sifirla():
    global _cached_failure_type_model, _cached_failure_type_paths
    with _failure_type_cache_lock:
        _cached_failure_type_model = None
        _cached_failure_type_paths = None
    ariza_tipi_explainer_cache_sifirla()


def _json_oku(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            metadata = json.load(stream)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ModelHizmetiHatasi() from exc
    if not isinstance(metadata, dict):
        raise ModelHizmetiHatasi()
    return metadata


def _gecerli_checksum(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _gecerli_olasilik(value):
    return (
        not isinstance(value, (bool, np.bool_))
        and isinstance(value, (int, float, np.integer, np.floating))
        and np.isfinite(value)
        and 0 <= value <= 1
    )


def _runtime_surumu_dogrula(metadata):
    runtime = metadata.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("Runtime metadata sözleşmesi geçersiz")
    training_version = runtime.get("scikit_learn")
    if not isinstance(training_version, str) or training_version != sklearn.__version__:
        raise ValueError("Scikit-learn runtime sürümü uyumsuz")


def _metadata_oku(path):
    metadata = _json_oku(path)
    try:
        required = {
            "model_version",
            "pipeline_version",
            "feature_columns",
            "threshold",
            "artifact",
            "runtime",
        }
        if not required <= metadata.keys():
            raise ValueError("Eksik metadata")
        _runtime_surumu_dogrula(metadata)
        valid = (
            metadata["model_version"] == MODEL_VERSION
            and metadata["pipeline_version"] == PIPELINE_VERSION
            and tuple(metadata["feature_columns"]) == MODEL_FEATURE_COLUMNS
            and _gecerli_olasilik(metadata["threshold"])
            and _gecerli_checksum(metadata["artifact"].get("sha256"))
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ModelHizmetiHatasi() from exc
    if not valid:
        raise ModelHizmetiHatasi()
    return metadata


def _ariza_tipi_metadata_oku(path):
    metadata = _json_oku(path)
    try:
        required = {
            "model_version",
            "pipeline_version",
            "feature_columns",
            "target_labels",
            "thresholds",
            "selected_candidate",
            "artifact",
            "runtime",
        }
        if not required <= metadata.keys():
            raise ValueError("Eksik metadata")
        _runtime_surumu_dogrula(metadata)
        targets = tuple(metadata["target_labels"])
        thresholds = metadata["thresholds"]
        valid = (
            metadata["model_version"] == FAILURE_TYPE_MODEL_VERSION
            and metadata["pipeline_version"] == PIPELINE_VERSION
            and tuple(metadata["feature_columns"]) == MODEL_FEATURE_COLUMNS
            and targets == MODELED_FAILURE_TYPE_COLUMNS
            and isinstance(thresholds, dict)
            and set(thresholds) == set(targets)
            and all(_gecerli_olasilik(thresholds[label]) for label in targets)
            and _gecerli_checksum(metadata["artifact"].get("sha256"))
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ModelHizmetiHatasi() from exc
    if not valid:
        raise ModelHizmetiHatasi()
    return metadata


def _pozitif_sinif_indeksi(pipeline):
    matches = [
        index
        for index, value in enumerate(getattr(pipeline, "classes_", ()))
        if not isinstance(value, (bool, np.bool_)) and value == 1
    ]
    if len(matches) != 1:
        raise ValueError("Pozitif sınıf sözleşmesi geçersiz")
    return matches[0]


def _pozitif_olasilik(pipeline, features):
    positive_index = _pozitif_sinif_indeksi(pipeline)
    probabilities = np.asarray(pipeline.predict_proba(features))
    if (
        probabilities.ndim != 2
        or probabilities.shape[0] != 1
        or positive_index >= probabilities.shape[1]
    ):
        raise ValueError("Olasılık şekli geçersiz")
    probability = probabilities[0, positive_index]
    if not _gecerli_olasilik(probability):
        raise ValueError("Olasılık değeri geçersiz")
    return float(probability)


def _model_yukle(artifact_path, metadata_path):
    metadata = _metadata_oku(metadata_path)
    if not Path(artifact_path).is_file():
        raise ModelHizmetiHatasi()
    try:
        artifact = load_trusted_artifact(
            artifact_path, expected_sha256=metadata["artifact"]["sha256"]
        )
        inner, pipeline = artifact.get("metadata"), artifact.get("pipeline")
        if not isinstance(inner, dict) or any(
            inner.get(key) != metadata[key]
            for key in (
                "model_version",
                "pipeline_version",
                "feature_columns",
                "threshold",
            )
        ):
            raise ValueError("Artefakt metadata uyuşmazlığı")
        _pozitif_sinif_indeksi(pipeline)
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
    return YukluModel(
        pipeline,
        float(metadata["threshold"]),
        metadata["model_version"],
        metadata["pipeline_version"],
    )


def _ariza_tipi_model_yukle(artifact_path, metadata_path):
    metadata = _ariza_tipi_metadata_oku(metadata_path)
    if not Path(artifact_path).is_file():
        raise ModelHizmetiHatasi()
    try:
        artifact = load_trusted_failure_type_artifact(
            artifact_path,
            expected_sha256=metadata["artifact"]["sha256"],
            expected_metadata=metadata,
        )
        pipelines = artifact["pipelines"]
        for pipeline in pipelines.values():
            _pozitif_sinif_indeksi(pipeline)
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
    return YukluArizaTipiModeli(
        pipelines,
        {
            label: float(metadata["thresholds"][label])
            for label in MODELED_FAILURE_TYPE_COLUMNS
        },
        metadata["model_version"],
        metadata["pipeline_version"],
    )


def modeli_getir(*, artifact_path=None, metadata_path=None):
    global _cached_model, _cached_paths
    paths = (
        str(artifact_path or settings.MODEL_ARTIFACT_PATH),
        str(metadata_path or settings.MODEL_METADATA_PATH),
    )
    if _cached_model is not None and _cached_paths == paths:
        return _cached_model
    with _binary_cache_lock:
        if _cached_model is None or _cached_paths != paths:
            loaded = _model_yukle(*paths)
            _cached_model, _cached_paths = loaded, paths
            binary_explainer_cache_sifirla()
    return _cached_model


def ariza_tipi_modeli_getir(*, artifact_path=None, metadata_path=None):
    global _cached_failure_type_model, _cached_failure_type_paths
    paths = (
        str(artifact_path or settings.FAILURE_TYPE_MODEL_ARTIFACT_PATH),
        str(metadata_path or settings.FAILURE_TYPE_MODEL_METADATA_PATH),
    )
    if _cached_failure_type_model is not None and _cached_failure_type_paths == paths:
        return _cached_failure_type_model
    with _failure_type_cache_lock:
        if _cached_failure_type_model is None or _cached_failure_type_paths != paths:
            loaded = _ariza_tipi_model_yukle(*paths)
            _cached_failure_type_model, _cached_failure_type_paths = loaded, paths
            ariza_tipi_explainer_cache_sifirla()
    return _cached_failure_type_model


def _ozellikleri_hazirla(sensor_verisi):
    model_girdilerini_dogrula(sensor_verisi)
    return feature_frame(add_engineered_features(pd.DataFrame([dict(sensor_verisi)])))


def _binary_risk_hesapla(features, model):
    risk = _pozitif_olasilik(model.pipeline, features)
    return {
        "risk_orani": risk,
        "risk_uyarisi": risk >= model.threshold,
        "threshold": model.threshold,
        "model_version": model.model_version,
        "pipeline_version": model.pipeline_version,
    }


def risk_tahmini_yap(sensor_verisi, *, model=None):
    try:
        result = _binary_risk_hesapla(
            _ozellikleri_hazirla(sensor_verisi), model or modeli_getir()
        )
        result["input_domain_contract_surumu"] = input_domain_contract_getir()[
            "contract_version"
        ]
        return result
    except ModelHizmetiHatasi:
        raise
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc


def _ariza_tipi_degerlendir(features, model):
    results = {}
    try:
        for label in MODELED_FAILURE_TYPE_COLUMNS:
            probability = _pozitif_olasilik(model.pipelines[label], features)
            threshold = model.thresholds[label]
            results[label] = {
                "kod": label,
                "olasilik": probability,
                "threshold": threshold,
                "esik_asildi": probability >= threshold,
            }
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
    order = {label: index for index, label in enumerate(GUVENILIR_FIZIKSEL_TIPLER)}
    trusted = [
        {key: result[key] for key in ("kod", "olasilik", "threshold")}
        for label in GUVENILIR_FIZIKSEL_TIPLER
        if (result := results[label])["esik_asildi"]
    ]
    trusted.sort(key=lambda item: (-item["olasilik"], order[item["kod"]]))
    experimental = [
        {
            **results[label],
            "guven_durumu": YETERSIZ_DESTEK,
            "operasyonel_kullanima_uygun": False,
        }
        for label in DENEYSEL_FIZIKSEL_TIPLER
    ]
    return {
        "durum": "DEGERLENDIRILDI",
        "model_version": model.model_version,
        "pipeline_version": model.pipeline_version,
        "guvenilir_adaylar": trusted,
        "deneysel_sinyaller": experimental,
        "belirsiz_fiziksel_tip": not trusted,
    }


def hiyerarsik_risk_tahmini_yap(
    sensor_verisi, *, binary_model=None, failure_type_model=None, features=None
):
    try:
        features = (
            features if features is not None else _ozellikleri_hazirla(sensor_verisi)
        )
        binary_snapshot = binary_model or modeli_getir()
        result = _binary_risk_hesapla(features, binary_snapshot)
        result["input_domain_contract_surumu"] = input_domain_contract_getir()[
            "contract_version"
        ]
        if not result["risk_uyarisi"]:
            result["ariza_tipi_degerlendirmesi"] = {
                "durum": "RISK_ESIK_ALTINDA",
                "guvenilir_adaylar": [],
                "deneysel_sinyaller": [],
                "belirsiz_fiziksel_tip": False,
            }
            result["aciklanabilirlik"] = {
                "durum": "RISK_ESIK_ALTINDA",
                "risk_aciklamasi": None,
            }
            return result
        failure_snapshot = failure_type_model or ariza_tipi_modeli_getir()
        evaluation = _ariza_tipi_degerlendir(features, failure_snapshot)
        result["aciklanabilirlik"] = {
            "durum": "ACIKLANDI",
            "risk_aciklamasi": aciklama_uret(
                binary_snapshot.pipeline,
                features,
                target="machine_failure",
                probability=result["risk_orani"],
                top_n=settings.SHAP_TOP_N,
            ),
        }
        for candidate in evaluation["guvenilir_adaylar"]:
            label = candidate["kod"]
            candidate["aciklama"] = aciklama_uret(
                failure_snapshot.pipelines[label],
                features,
                target=label,
                probability=candidate["olasilik"],
                top_n=settings.SHAP_TOP_N,
                label=label,
            )
        for signal in evaluation["deneysel_sinyaller"]:
            label = signal["kod"]
            if signal["esik_asildi"]:
                signal["aciklama"] = aciklama_uret(
                    failure_snapshot.pipelines[label],
                    features,
                    target=label,
                    probability=signal["olasilik"],
                    top_n=settings.SHAP_TOP_N,
                    label=label,
                )
        result["ariza_tipi_degerlendirmesi"] = evaluation
        return result
    except ModelHizmetiHatasi:
        raise
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
