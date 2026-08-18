import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import sklearn

from .artifact import artifact_sha256
from .data_contract import (
    MODEL_FEATURE_COLUMNS,
    MODELED_FAILURE_TYPE_COLUMNS,
    PIPELINE_VERSION,
)
from .failure_type_modeling import (
    evaluate_failure_types,
    failure_type_candidates,
    fit_candidate,
    predict_probabilities,
    select_global_candidate,
    select_label_thresholds,
)
from .features import add_engineered_features
from .loaders import (
    DEFAULT_PREPARED_PATH,
    REPO_ROOT,
    file_sha256,
    load_dataset,
    resolve_path,
)
from .training import RANDOM_SEED, split_dataset, write_metadata
from .validation import require_quality

MODEL_VERSION = "failure-type-1.0.0"
DEFAULT_ARTIFACT = REPO_ROOT / "ml" / "artifacts" / f"{MODEL_VERSION}.joblib"
DEFAULT_METADATA = REPO_ROOT / "data" / "metadata" / "failure_type_model.json"
ANALYSIS_METADATA = REPO_ROOT / "data" / "metadata" / "failure_label_analysis.json"


def _class_counts(parts):
    return {
        split_name: {
            label: {
                "positive": int(part[label].sum()),
                "negative": int(len(part) - part[label].sum()),
            }
            for label in MODELED_FAILURE_TYPE_COLUMNS
        }
        for split_name, part in parts.items()
    }


def train_failure_type_model(source=None, artifact_path=None, metadata_path=None):
    source_path = resolve_path(source)
    provenance = json.loads(ANALYSIS_METADATA.read_text(encoding="utf-8"))
    expected_source_sha256 = None if source else provenance["source_sha256"]
    raw = load_dataset(source_path, expected_sha256=expected_source_sha256)
    quality = require_quality(raw)
    frame = add_engineered_features(raw)
    train, validation, test = split_dataset(frame)
    fitted = {}
    evaluations = {}
    for name, estimator in failure_type_candidates().items():
        pipelines, result = fit_candidate(estimator, train, validation)
        model = next(iter(pipelines.values())).named_steps["model"]
        evaluations[name] = {
            "model_family": type(model).__name__,
            "class_weight": model.class_weight,
            **result,
        }
        fitted[name] = pipelines
    selected_name = select_global_candidate(evaluations)
    selected = fitted[selected_name]
    validation_probabilities = predict_probabilities(selected, validation)
    thresholds, threshold_comparison = select_label_thresholds(
        validation, validation_probabilities
    )
    validation_metrics = evaluate_failure_types(
        validation, validation_probabilities, thresholds
    )
    test_probabilities = predict_probabilities(selected, test)
    test_metrics = evaluate_failure_types(test, test_probabilities, thresholds)
    selected_model = next(iter(selected.values())).named_steps["model"]
    prepared_sha256 = None
    if not source and DEFAULT_PREPARED_PATH.is_file():
        prepared_sha256 = file_sha256(DEFAULT_PREPARED_PATH)
    if not source and prepared_sha256 != provenance["prepared_source_sha256"]:
        raise ValueError(
            "Hazırlanmış veri checksum değeri Sprint 10 analiziyle uyumsuz."
        )
    parts = {"train": train, "validation": validation, "test": test}
    support_warnings = [
        {
            "label": label,
            "validation_support": int(validation[label].sum()),
            "test_support": int(test[label].sum()),
            "warning": "Az destek nedeniyle metrikler yüksek varyanslı olabilir.",
        }
        for label in MODELED_FAILURE_TYPE_COLUMNS
        if validation[label].sum() < 20 or test[label].sum() < 20
    ]
    metadata = {
        "model_version": MODEL_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "task": "physical_failure_type_prediction",
        "problem_type": "hierarchical_multi_label_binary_relevance",
        "target_labels": list(MODELED_FAILURE_TYPE_COLUMNS),
        "excluded_labels": ["RNF"],
        "excluded_label_policy": (
            "RNF model dışında raporlanır ve genel teknik incelemeye yönlendirilir."
        ),
        "selected_candidate": selected_name,
        "selected_model_family": type(selected_model).__name__,
        "selected_class_weight": selected_model.class_weight,
        "thresholds": thresholds,
        "threshold_policy": "maximize_validation_f1_then_recall_then_lower_threshold",
        "threshold_comparison": threshold_comparison,
        "random_seed": RANDOM_SEED,
        "split": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
            "stratified_target": "makine_arizasi",
        },
        "class_counts": _class_counts(parts),
        "feature_columns": list(MODEL_FEATURE_COLUMNS),
        "excluded_feature_columns": [
            "makine_arizasi",
            "TWF",
            "HDF",
            "PWF",
            "OSF",
            "RNF",
            "udi",
            "urun_kodu",
            "machine_id",
            "timestamp",
        ],
        "source_sha256": file_sha256(source_path),
        "prepared_source_sha256": prepared_sha256,
        "candidate_validation": evaluations,
        "selected_validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "quality_warnings": [
            issue.to_dict() for issue in quality.issues if issue.severity == "warning"
        ],
        "support_warnings": support_warnings,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    artifact_path = Path(artifact_path) if artifact_path else DEFAULT_ARTIFACT
    metadata_path = Path(metadata_path) if metadata_path else DEFAULT_METADATA
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = artifact_path.with_suffix(".joblib.tmp")
    try:
        joblib.dump(
            {"pipelines": selected, "metadata": metadata}, temporary, compress=3
        )
        os.replace(temporary, artifact_path)
    finally:
        temporary.unlink(missing_ok=True)
    metadata["artifact"] = {
        "relative_path": f"ml/artifacts/{artifact_path.name}",
        "sha256": artifact_sha256(artifact_path),
        "size_bytes": artifact_path.stat().st_size,
    }
    write_metadata(metadata, metadata_path)
    return metadata
