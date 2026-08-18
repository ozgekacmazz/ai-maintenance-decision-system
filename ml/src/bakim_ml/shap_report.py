import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import numpy as np

from .artifact import load_trusted_artifact, load_trusted_failure_type_artifact
from .data_contract import MODELED_FAILURE_TYPE_COLUMNS
from .explainability import (
    explain_binary_prediction,
    explain_failure_type_prediction,
)
from .loaders import (
    DEFAULT_PREPARED_PATH,
    REPO_ROOT,
    file_sha256,
    load_prepared_dataset,
)
from .training import RANDOM_SEED, split_dataset, write_metadata

ANALYSIS_VERSION = "shap-analysis-1.0.0"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "metadata" / "shap_analysis.json"
BINARY_METADATA = REPO_ROOT / "data" / "metadata" / "binary_failure_model.json"
FAILURE_TYPE_METADATA = REPO_ROOT / "data" / "metadata" / "failure_type_model.json"


def deterministic_fingerprint(document):
    content = {
        key: value
        for key, value in document.items()
        if key not in {"created_at", "fingerprint"}
    }
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _read_metadata(path):
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Model metadata dosyası okunamadı.") from exc
    if not isinstance(document, dict):
        raise ValueError("Model metadata sözleşmesi geçersiz.")
    return document


def _global_importance(explanations):
    feature_names = tuple(
        item["feature"] for item in explanations[0]["feature_contributions"]
    )
    totals = {name: [] for name in feature_names}
    for explanation in explanations:
        contributions = {
            item["feature"]: item["shap_value"]
            for item in explanation["feature_contributions"]
        }
        if set(contributions) != set(feature_names):
            raise ValueError("Açıklama feature sözleşmesi tutarsız.")
        for name in feature_names:
            totals[name].append(abs(contributions[name]))
    result = [
        {"feature": name, "mean_abs_shap": float(np.mean(values))}
        for name, values in totals.items()
    ]
    if not all(np.isfinite(item["mean_abs_shap"]) for item in result):
        raise ValueError("Global SHAP değerleri sonlu değil.")
    result.sort(key=lambda item: (-item["mean_abs_shap"], item["feature"]))
    return result


def _select_validation_sample(validation, sample_size, *, random_seed=RANDOM_SEED):
    if (
        isinstance(sample_size, bool)
        or not isinstance(sample_size, int)
        or sample_size < 1
    ):
        raise ValueError("sample_size pozitif bir tam sayı olmalıdır.")
    if sample_size > len(validation):
        raise ValueError("sample_size validation split boyutunu aşamaz.")
    return validation.sample(
        n=sample_size,
        replace=False,
        random_state=random_seed,
    ).sort_index()


def generate_shap_analysis(*, sample_size=25, output_path=None):
    binary_metadata = _read_metadata(BINARY_METADATA)
    failure_metadata = _read_metadata(FAILURE_TYPE_METADATA)
    frame = load_prepared_dataset(
        DEFAULT_PREPARED_PATH,
        expected_sha256=failure_metadata["prepared_source_sha256"],
    )
    _, validation, _ = split_dataset(frame)
    sample = _select_validation_sample(validation, sample_size)

    binary_artifact = load_trusted_artifact(
        REPO_ROOT / binary_metadata["artifact"]["relative_path"],
        expected_sha256=binary_metadata["artifact"]["sha256"],
    )
    failure_artifact = load_trusted_failure_type_artifact(
        REPO_ROOT / failure_metadata["artifact"]["relative_path"],
        expected_sha256=failure_metadata["artifact"]["sha256"],
        expected_metadata=failure_metadata,
    )
    feature_count = len(
        binary_artifact["pipeline"].named_steps["preprocessor"].get_feature_names_out()
    )
    binary_explanations = [
        explain_binary_prediction(binary_artifact, row, top_n=feature_count)
        for _, row in sample.iterrows()
    ]
    target_importance = {"machine_failure": _global_importance(binary_explanations)}
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        explanations = [
            explain_failure_type_prediction(
                failure_artifact, row, label, top_n=feature_count
            )
            for _, row in sample.iterrows()
        ]
        target_importance[label] = _global_importance(explanations)

    document = {
        "analysis_version": ANALYSIS_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "sample": {
            "split": "validation",
            "size": sample_size,
            "selection": "seeded_random_without_replacement_then_source_index_sort",
            "seed": RANDOM_SEED,
        },
        "prepared_source_sha256": file_sha256(DEFAULT_PREPARED_PATH),
        "models": {
            "binary": {
                "model_version": binary_metadata["model_version"],
                "pipeline_version": binary_metadata["pipeline_version"],
                "artifact_sha256": binary_metadata["artifact"]["sha256"],
            },
            "failure_type": {
                "model_version": failure_metadata["model_version"],
                "pipeline_version": failure_metadata["pipeline_version"],
                "artifact_sha256": failure_metadata["artifact"]["sha256"],
            },
        },
        "feature_names": list(
            binary_artifact["pipeline"]
            .named_steps["preprocessor"]
            .get_feature_names_out()
        ),
        "global_mean_absolute_shap": target_importance,
    }
    document["fingerprint"] = deterministic_fingerprint(document)
    write_metadata(document, output_path or DEFAULT_OUTPUT)
    return document
