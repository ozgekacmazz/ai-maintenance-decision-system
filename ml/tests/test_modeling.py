import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from bakim_ml.artifact import (
    ArtifactValidationError,
    artifact_sha256,
    load_trusted_artifact,
)
from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from bakim_ml.features import add_engineered_features
from bakim_ml.modeling import (
    build_pipeline,
    candidate_models,
    evaluate,
    feature_frame,
    select_candidate_by_pr_auc,
    select_hypothetical_cost_threshold,
    select_threshold,
    threshold_comparison,
)
from bakim_ml.training import split_dataset, write_metadata


def model_frame(raw_frame):
    frame = add_engineered_features(
        pd.concat([raw_frame] * 50, ignore_index=True).rename(
            columns={
                "UDI": "udi",
                "Product ID": "urun_kodu",
                "Type": "urun_tipi",
                "Air temperature [K]": "hava_sicakligi_k",
                "Process temperature [K]": "proses_sicakligi_k",
                "Rotational speed [rpm]": "donus_hizi_rpm",
                "Torque [Nm]": "tork_nm",
                "Tool wear [min]": "takim_asinmasi_dk",
                "Machine failure": "makine_arizasi",
            }
        )
    )
    frame["udi"] = range(1, len(frame) + 1)
    return frame


def test_feature_frame_has_no_target_or_id_leakage(raw_frame):
    selected = feature_frame(model_frame(raw_frame))
    assert tuple(selected.columns) == MODEL_FEATURE_COLUMNS
    assert not {"makine_arizasi", "udi", "urun_kodu", "TWF"} & set(selected.columns)


def test_stratified_split_is_deterministic_and_disjoint(raw_frame):
    frame = model_frame(raw_frame)
    first = split_dataset(frame)
    second = split_dataset(frame)
    assert [len(part) for part in first] == [70, 15, 15]
    for left, right in zip(first, second, strict=True):
        assert left.index.tolist() == right.index.tolist()
    index_sets = [set(part.index) for part in first]
    assert not index_sets[0] & index_sets[1]
    assert not index_sets[0] & index_sets[2]
    assert not index_sets[1] & index_sets[2]
    assert set.union(*index_sets) == set(frame.index)
    assert sum(part["makine_arizasi"].sum() for part in first) == 50


def test_threshold_maximizes_validation_f1():
    target = np.array([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.4, 0.45, 0.9])
    threshold = select_threshold(target, probabilities)
    assert threshold == pytest.approx(0.45)
    metrics = evaluate(target, probabilities, threshold)
    assert metrics.false_negative == 0 and metrics.true_positive == 2


def test_four_required_candidates_and_pr_auc_selection_ignores_accuracy():
    candidates = candidate_models()
    assert set(candidates) == {
        "logistic_regression_none",
        "logistic_regression_balanced",
        "random_forest_none",
        "random_forest_balanced",
    }
    assert candidates["logistic_regression_none"].class_weight is None
    assert candidates["logistic_regression_balanced"].class_weight == "balanced"
    assert candidates["random_forest_none"].class_weight is None
    assert candidates["random_forest_balanced"].class_weight == "balanced"
    evaluations = {
        "high_accuracy": {"validation_pr_auc": 0.4, "accuracy": 0.99},
        "high_pr_auc": {"validation_pr_auc": 0.8, "accuracy": 0.50},
    }
    assert select_candidate_by_pr_auc(evaluations) == "high_pr_auc"


def test_max_f1_threshold_tie_prefers_higher_recall_and_not_cost_policy():
    target = np.array([0, 0, 1, 1])
    probabilities = np.array([0.2, 0.4, 0.4, 0.8])
    selected = select_threshold(target, probabilities)
    selected_metrics = evaluate(target, probabilities, selected)
    all_metrics = [
        evaluate(target, probabilities, threshold)
        for threshold in np.unique(np.concatenate(([0.0], probabilities, [1.0])))
    ]
    assert selected_metrics.f1 == max(metric.f1 for metric in all_metrics)
    tied_recalls = [
        metric.recall
        for metric in all_metrics
        if metric.f1 == pytest.approx(selected_metrics.f1)
    ]
    assert selected_metrics.recall == max(tied_recalls)
    cost_threshold = select_hypothetical_cost_threshold(target, probabilities)
    comparison = threshold_comparison(target, probabilities)
    assert comparison["max_validation_f1"]["threshold"] == selected
    assert comparison["hypothetical_cost_5_to_1"]["threshold"] == cost_threshold


def test_pipeline_only_fits_training_data(raw_frame):
    frame = model_frame(raw_frame)
    train, validation, _ = split_dataset(frame)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(feature_frame(train), train["makine_arizasi"])
    assert pipeline.predict_proba(feature_frame(validation)).shape == (15, 2)


def test_artifact_checksum_and_contract_validation(raw_frame, tmp_path):
    frame = model_frame(raw_frame)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(feature_frame(frame), frame["makine_arizasi"])
    path = tmp_path / "model.joblib"
    joblib.dump(
        {
            "pipeline": pipeline,
            "metadata": {
                "pipeline_version": PIPELINE_VERSION,
                "feature_columns": list(MODEL_FEATURE_COLUMNS),
                "threshold": 0.5,
            },
        },
        path,
    )
    artifact = load_trusted_artifact(path, expected_sha256=artifact_sha256(path))
    assert artifact["metadata"]["threshold"] == 0.5
    with pytest.raises(ArtifactValidationError):
        load_trusted_artifact(path, expected_sha256="0" * 64)


def test_metadata_rejects_nan_and_infinity(tmp_path):
    path = tmp_path / "metadata.json"
    with pytest.raises(ValueError):
        write_metadata({"metric": float("nan")}, path)
    with pytest.raises(ValueError):
        write_metadata({"metric": float("inf")}, path)
    assert not path.exists()
