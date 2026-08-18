from hashlib import sha256
from pathlib import Path

import joblib

from .data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION


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
