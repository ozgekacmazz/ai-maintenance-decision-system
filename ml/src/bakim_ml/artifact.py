import math
from hashlib import sha256
from pathlib import Path

import joblib

from .data_contract import (
    MODEL_FEATURE_COLUMNS,
    MODELED_FAILURE_TYPE_COLUMNS,
    PIPELINE_VERSION,
)


class ArtifactValidationError(Exception):
    pass


def artifact_sha256(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_trusted_artifact(path, *, expected_sha256):
    """Yalnız güvenilir yerel kaynaktan gelen, checksum'ı bilinen artefaktı yükler."""
    if artifact_sha256(path) != expected_sha256:
        raise ArtifactValidationError(
            "Model artefaktı checksum doğrulamasından geçemedi."
        )
    artifact = joblib.load(path)
    metadata = artifact.get("metadata", {})
    if metadata.get("pipeline_version") != PIPELINE_VERSION:
        raise ArtifactValidationError("Model pipeline sürümü uyumsuz.")
    if tuple(metadata.get("feature_columns", ())) != MODEL_FEATURE_COLUMNS:
        raise ArtifactValidationError("Model feature sözleşmesi uyumsuz.")
    threshold = metadata.get("threshold")
    if not isinstance(threshold, float) or not 0 <= threshold <= 1:
        raise ArtifactValidationError("Model threshold metadata'sı geçersiz.")
    if not hasattr(artifact.get("pipeline"), "predict_proba"):
        raise ArtifactValidationError("Model pipeline tahmin arayüzünü sağlamıyor.")
    return artifact


def load_trusted_failure_type_artifact(
    path, *, expected_sha256, expected_metadata=None
):
    if artifact_sha256(path) != expected_sha256:
        raise ArtifactValidationError(
            "Arıza tipi artefaktı checksum doğrulamasından geçemedi."
        )
    artifact = joblib.load(path)
    if not isinstance(artifact, dict):
        raise ArtifactValidationError("Arıza tipi artefakt biçimi geçersiz.")
    metadata = artifact.get("metadata", {})
    pipelines = artifact.get("pipelines", {})
    targets = tuple(metadata.get("target_labels", ()))
    thresholds = metadata.get("thresholds", {})
    if metadata.get("model_version") != "failure-type-1.0.0":
        raise ArtifactValidationError("Arıza tipi model sürümü uyumsuz.")
    if metadata.get("pipeline_version") != PIPELINE_VERSION:
        raise ArtifactValidationError("Arıza tipi pipeline sürümü uyumsuz.")
    if tuple(metadata.get("feature_columns", ())) != MODEL_FEATURE_COLUMNS:
        raise ArtifactValidationError("Arıza tipi feature sözleşmesi uyumsuz.")
    if targets != MODELED_FAILURE_TYPE_COLUMNS or "RNF" in targets:
        raise ArtifactValidationError("Arıza tipi hedef sözleşmesi uyumsuz.")
    if set(thresholds) != set(targets) or set(pipelines) != set(targets):
        raise ArtifactValidationError("Pipeline veya threshold anahtarları uyumsuz.")
    for label in targets:
        threshold = thresholds[label]
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or not 0 <= threshold <= 1
        ):
            raise ArtifactValidationError("Arıza tipi threshold değeri geçersiz.")
        pipeline = pipelines[label]
        if not hasattr(pipeline, "predict_proba"):
            raise ArtifactValidationError("Arıza tipi pipeline arayüzü geçersiz.")
        classes = getattr(pipeline, "classes_", ())
        if 1 not in classes:
            raise ArtifactValidationError("Arıza tipi pozitif sınıfı bulunamadı.")
    if expected_metadata is not None:
        critical = (
            "model_version",
            "pipeline_version",
            "target_labels",
            "feature_columns",
            "thresholds",
            "selected_candidate",
        )
        if any(metadata.get(key) != expected_metadata.get(key) for key in critical):
            raise ArtifactValidationError("Artefakt ve tracked metadata uyumsuz.")
    return artifact
