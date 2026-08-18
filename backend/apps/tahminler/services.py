import json
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from bakim_ml.artifact import load_trusted_artifact
from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from bakim_ml.features import add_engineered_features
from bakim_ml.modeling import feature_frame
from django.conf import settings

from apps.tahminler.exceptions import ModelHizmetiHatasi

MODEL_VERSION = "binary-failure-1.0.0"
_cache_lock = threading.Lock()
_cached_model = None
_cached_paths = None


@dataclass(frozen=True)
class YukluModel:
    pipeline: object
    threshold: float
    model_version: str
    pipeline_version: str


def model_cache_sifirla():
    global _cached_model, _cached_paths
    with _cache_lock:
        _cached_model = None
        _cached_paths = None


def _metadata_oku(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            metadata = json.load(stream)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ModelHizmetiHatasi() from exc
    try:
        required = {
            "model_version",
            "pipeline_version",
            "feature_columns",
            "threshold",
            "artifact",
        }
        if not isinstance(metadata, dict) or not required <= metadata.keys():
            raise ValueError("Eksik metadata")
        checksum = metadata["artifact"].get("sha256")
        threshold = metadata["threshold"]
        valid = (
            metadata["model_version"] == MODEL_VERSION
            and metadata["pipeline_version"] == PIPELINE_VERSION
            and tuple(metadata["feature_columns"]) == MODEL_FEATURE_COLUMNS
            and not isinstance(threshold, bool)
            and isinstance(threshold, (int, float))
            and np.isfinite(threshold)
            and 0 <= threshold <= 1
            and isinstance(checksum, str)
            and len(checksum) == 64
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ModelHizmetiHatasi() from exc
    if not valid:
        raise ModelHizmetiHatasi()
    return metadata


def _model_yukle(artifact_path, metadata_path):
    metadata = _metadata_oku(metadata_path)
    if not Path(artifact_path).is_file():
        raise ModelHizmetiHatasi()
    try:
        artifact = load_trusted_artifact(
            artifact_path, expected_sha256=metadata["artifact"]["sha256"]
        )
        inner = artifact.get("metadata")
        pipeline = artifact.get("pipeline")
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
        if not hasattr(pipeline, "predict_proba"):
            raise ValueError("predict_proba yok")
        classes = getattr(pipeline, "classes_", None)
        if (
            classes is None
            or sum(
                value == 1 and not isinstance(value, (bool, np.bool_))
                for value in classes
            )
            != 1
        ):
            raise ValueError("Pozitif sınıf yok")
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
    return YukluModel(
        pipeline=pipeline,
        threshold=float(metadata["threshold"]),
        model_version=metadata["model_version"],
        pipeline_version=metadata["pipeline_version"],
    )


def modeli_getir(*, artifact_path=None, metadata_path=None):
    global _cached_model, _cached_paths
    paths = (
        str(artifact_path or settings.MODEL_ARTIFACT_PATH),
        str(metadata_path or settings.MODEL_METADATA_PATH),
    )
    if _cached_model is not None and _cached_paths == paths:
        return _cached_model
    with _cache_lock:
        if _cached_model is None or _cached_paths != paths:
            _cached_model = _model_yukle(*paths)
            _cached_paths = paths
    return _cached_model


def risk_tahmini_yap(sensor_verisi, *, model=None):
    model = model or modeli_getir()
    frame = pd.DataFrame([dict(sensor_verisi)])
    try:
        features = feature_frame(add_engineered_features(frame))
        probabilities = np.asarray(model.pipeline.predict_proba(features))
        positive_index = next(
            index
            for index, value in enumerate(model.pipeline.classes_)
            if value == 1 and not isinstance(value, (bool, np.bool_))
        )
        risk = float(probabilities[0, positive_index])
        if probabilities.shape[0] != 1 or not np.isfinite(risk) or not 0 <= risk <= 1:
            raise ValueError("Geçersiz olasılık")
    except Exception as exc:
        raise ModelHizmetiHatasi() from exc
    return {
        "risk_orani": risk,
        "risk_uyarisi": risk >= model.threshold,
        "threshold": model.threshold,
        "model_version": model.model_version,
        "pipeline_version": model.pipeline_version,
    }
