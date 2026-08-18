import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import sklearn
from sklearn.model_selection import train_test_split

from .artifact import artifact_sha256
from .data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from .features import add_engineered_features
from .loaders import REPO_ROOT, file_sha256, load_dataset, resolve_path
from .modeling import (
    RANDOM_SEED,
    build_pipeline,
    candidate_models,
    evaluate,
    feature_frame,
    select_candidate_by_pr_auc,
    threshold_comparison,
)
from .validation import require_quality

MODEL_VERSION = "binary-failure-1.0.0"
DEFAULT_ARTIFACT = REPO_ROOT / "ml" / "artifacts" / f"{MODEL_VERSION}.joblib"
DEFAULT_METADATA = REPO_ROOT / "data" / "metadata" / "binary_failure_model.json"


def write_metadata(document, path):
    serialized = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    Path(path).write_text(serialized + "\n", encoding="utf-8")


def split_dataset(frame):
    row_count = len(frame)
    test_count = round(row_count * 0.15)
    validation_count = round(row_count * 0.15)
    train_validation, test = train_test_split(
        frame,
        test_size=test_count,
        stratify=frame["makine_arizasi"],
        random_state=RANDOM_SEED,
    )
    train, validation = train_test_split(
        train_validation,
        test_size=validation_count,
        stratify=train_validation["makine_arizasi"],
        random_state=RANDOM_SEED,
    )
    return train, validation, test


def train_binary_model(source=None, artifact_path=None, metadata_path=None):
    source_path = resolve_path(source)
    raw = load_dataset(source_path)
    quality = require_quality(raw)
    frame = add_engineered_features(raw)
    train, validation, test = split_dataset(frame)
    evaluations = {}
    fitted = {}
    for name, estimator in candidate_models().items():
        pipeline = build_pipeline(estimator)
        fit_started = perf_counter()
        pipeline.fit(feature_frame(train), train["makine_arizasi"])
        fit_seconds = perf_counter() - fit_started
        inference_started = perf_counter()
        probabilities = pipeline.predict_proba(feature_frame(validation))[:, 1]
        inference_seconds = perf_counter() - inference_started
        metrics = evaluate(validation["makine_arizasi"], probabilities, 0.50)
        model = pipeline.named_steps["model"]
        evaluations[name] = {
            "model_family": type(model).__name__,
            "class_weight": model.class_weight,
            "hyperparameters": {
                key: model.get_params()[key]
                for key in (
                    "class_weight",
                    "max_iter",
                    "n_estimators",
                    "min_samples_leaf",
                )
                if key in model.get_params()
            },
            "validation_pr_auc": metrics.pr_auc,
            "threshold_0_50": metrics.to_dict(),
            "fit_seconds": fit_seconds,
            "inference_seconds": inference_seconds,
        }
        fitted[name] = pipeline
    selected_name = select_candidate_by_pr_auc(evaluations)
    selected = fitted[selected_name]
    validation_probabilities = selected.predict_proba(feature_frame(validation))[:, 1]
    comparisons = threshold_comparison(
        validation["makine_arizasi"], validation_probabilities
    )
    threshold = comparisons["max_validation_f1"]["threshold"]
    validation_metrics = evaluate(
        validation["makine_arizasi"], validation_probabilities, threshold
    )
    test_probabilities = selected.predict_proba(feature_frame(test))[:, 1]
    test_metrics = evaluate(test["makine_arizasi"], test_probabilities, threshold)
    metadata = {
        "model_version": MODEL_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "task": "binary_machine_failure",
        "selected_model": selected_name,
        "selected_model_family": type(selected.named_steps["model"]).__name__,
        "selected_class_weight": selected.named_steps["model"].class_weight,
        "threshold": float(threshold),
        "threshold_policy": "maximize_validation_f1_then_recall",
        "random_seed": RANDOM_SEED,
        "split": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
            "stratified": True,
        },
        "class_counts": {
            part: {
                str(key): int(value)
                for key, value in data["makine_arizasi"]
                .value_counts()
                .sort_index()
                .items()
            }
            for part, data in (
                ("train", train),
                ("validation", validation),
                ("test", test),
            )
        },
        "feature_columns": list(MODEL_FEATURE_COLUMNS),
        "target": "makine_arizasi",
        "excluded_columns": [
            "udi",
            "urun_kodu",
            "TWF",
            "HDF",
            "PWF",
            "OSF",
            "RNF",
            "machine_id",
            "timestamp",
        ],
        "source_sha256": file_sha256(source_path),
        "candidate_validation": evaluations,
        "threshold_comparison": comparisons,
        "selected_validation_metrics": validation_metrics.to_dict(),
        "test_metrics": test_metrics.to_dict(),
        "quality_warnings": [
            issue.to_dict() for issue in quality.issues if issue.severity == "warning"
        ],
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
        joblib.dump({"pipeline": selected, "metadata": metadata}, temporary, compress=3)
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
