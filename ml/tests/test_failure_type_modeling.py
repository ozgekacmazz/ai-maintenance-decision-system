import copy
import json
from hashlib import sha256

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from bakim_ml.artifact import (
    ArtifactValidationError,
    load_trusted_failure_type_artifact,
)
from bakim_ml.data_contract import (
    MODEL_FEATURE_COLUMNS,
    MODELED_FAILURE_TYPE_COLUMNS,
    PIPELINE_VERSION,
)
from bakim_ml.failure_type_modeling import (
    FailureTypeModelingError,
    evaluate_failure_types,
    failure_type_candidates,
    fit_candidate,
    predict_probabilities,
    select_global_candidate,
    select_label_thresholds,
)
from bakim_ml.features import add_engineered_features
from bakim_ml.modeling import feature_frame, select_threshold, threshold_candidates
from bakim_ml.training import split_dataset, write_metadata


class FakePipeline:
    classes_ = np.asarray((0, 1))

    def predict_proba(self, frame):
        return np.tile((0.4, 0.6), (len(frame), 1))


class PredictOnlyPipeline:
    classes_ = np.asarray((0, 1))


class NoPositivePipeline(FakePipeline):
    classes_ = np.asarray((0,))


class ReversedPipeline:
    classes_ = np.asarray((1, 0))

    def predict_proba(self, frame):
        return np.tile((0.7, 0.3), (len(frame), 1))


class BooleanPositivePipeline(FakePipeline):
    classes_ = np.asarray((False, True))


class DuplicatePositivePipeline(FakePipeline):
    classes_ = np.asarray((1, 1))


def model_frame():
    rows = []
    for index in range(100):
        machine_failure = index % 5 != 0
        rows.append(
            {
                "urun_tipi": ("L", "M", "H")[index % 3],
                "hava_sicakligi_k": 298.0 + index % 5,
                "proses_sicakligi_k": 308.0 + index % 5,
                "donus_hizi_rpm": 1400 + index,
                "tork_nm": 30.0 + index % 20,
                "takim_asinmasi_dk": index % 50,
                "makine_arizasi": int(machine_failure),
                "TWF": int(index % 5 == 1),
                "HDF": int(index % 5 == 2),
                "PWF": int(index % 5 == 3),
                "OSF": int(index % 5 == 4),
                "RNF": int(index == 0),
                "udi": index + 1,
                "urun_kodu": f"L{index:05d}",
                "machine_id": f"M-{index % 20 + 1:03d}",
                "timestamp": f"2020-01-01T00:{index % 60:02d}:00Z",
            }
        )
    return add_engineered_features(pd.DataFrame(rows))


def artifact_metadata():
    return {
        "model_version": "failure-type-1.0.0",
        "pipeline_version": PIPELINE_VERSION,
        "target_labels": list(MODELED_FAILURE_TYPE_COLUMNS),
        "feature_columns": list(MODEL_FEATURE_COLUMNS),
        "thresholds": {label: 0.5 for label in MODELED_FAILURE_TYPE_COLUMNS},
        "selected_candidate": "logistic_regression_none",
    }


def write_artifact(tmp_path, metadata=None, pipelines=None):
    path = tmp_path / "failure.joblib"
    joblib.dump(
        {
            "metadata": metadata or artifact_metadata(),
            "pipelines": pipelines
            or {label: FakePipeline() for label in MODELED_FAILURE_TYPE_COLUMNS},
        },
        path,
    )
    return path, sha256(path.read_bytes()).hexdigest()


def test_targets_features_leakage_and_input_immutability():
    assert MODELED_FAILURE_TYPE_COLUMNS == ("TWF", "HDF", "PWF", "OSF")
    assert "RNF" not in MODELED_FAILURE_TYPE_COLUMNS
    forbidden = {
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
    }
    assert not forbidden & set(MODEL_FEATURE_COLUMNS)
    frame = model_frame()
    original = frame.copy(deep=True)
    assert tuple(feature_frame(frame).columns) == MODEL_FEATURE_COLUMNS
    pd.testing.assert_frame_equal(frame, original)


def test_split_contract_supports_and_candidates():
    frame = model_frame()
    first = split_dataset(frame)
    second = split_dataset(frame)
    assert [len(part) for part in first] == [70, 15, 15]
    assert [part.index.tolist() for part in first] == [
        part.index.tolist() for part in second
    ]
    sets = [set(part.index) for part in first]
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    assert set.union(*sets) == set(frame.index)
    assert set(failure_type_candidates()) == {
        "logistic_regression_none",
        "logistic_regression_balanced",
        "random_forest_none",
        "random_forest_balanced",
    }
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        assert sum(int(part[label].sum()) for part in first) == 20


def test_candidate_builds_four_independent_pipelines():
    train, validation, _ = split_dataset(model_frame())
    pipelines, result = fit_candidate(
        LogisticRegression(max_iter=2000, random_state=42), train, validation
    )
    assert tuple(pipelines) == MODELED_FAILURE_TYPE_COLUMNS
    assert len({id(pipeline) for pipeline in pipelines.values()}) == 4
    assert set(result["label_metrics_at_0_50"]) == set(MODELED_FAILURE_TYPE_COLUMNS)


def test_global_selection_uses_validation_and_deterministic_ties():
    evaluations = {
        "rf": {
            "validation_macro_pr_auc": 0.8,
            "validation_macro_recall_at_0_50": 0.7,
            "model_family": "RandomForestClassifier",
            "class_weight": None,
            "accuracy": 1.0,
            "test_score": 1.0,
        },
        "lr_balanced": {
            "validation_macro_pr_auc": 0.8,
            "validation_macro_recall_at_0_50": 0.7,
            "model_family": "LogisticRegression",
            "class_weight": "balanced",
            "accuracy": 0.0,
            "test_score": 0.0,
        },
        "lr_none": {
            "validation_macro_pr_auc": 0.8,
            "validation_macro_recall_at_0_50": 0.7,
            "model_family": "LogisticRegression",
            "class_weight": None,
            "accuracy": 0.0,
            "test_score": 0.0,
        },
    }
    assert select_global_candidate(evaluations) == "lr_none"
    evaluations["rf"]["validation_macro_pr_auc"] = 0.81
    assert select_global_candidate(evaluations) == "rf"


def test_each_threshold_uses_own_validation_values(monkeypatch):
    frame = pd.DataFrame(
        {label: [0, 0, 1, 1] for label in MODELED_FAILURE_TYPE_COLUMNS}
    )
    probabilities = {
        label: np.asarray([0.1, 0.2, 0.7 + index * 0.01, 0.9])
        for index, label in enumerate(MODELED_FAILURE_TYPE_COLUMNS)
    }
    seen = []

    def recording_select(target, probability):
        seen.append(probability.copy())
        return select_threshold(target, probability)

    monkeypatch.setattr(
        "bakim_ml.failure_type_modeling.select_threshold", recording_select
    )
    thresholds, comparisons = select_label_thresholds(frame, probabilities)
    assert set(thresholds) == set(MODELED_FAILURE_TYPE_COLUMNS)
    assert all(
        np.array_equal(seen[index], probabilities[label])
        for index, label in enumerate(MODELED_FAILURE_TYPE_COLUMNS)
    )
    assert all(
        comparisons[label]["max_validation_f1"]["threshold"] == thresholds[label]
        for label in MODELED_FAILURE_TYPE_COLUMNS
    )
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        expected = select_threshold(frame[label], probabilities[label])
        assert thresholds[label] == expected
        assert thresholds[label] in threshold_candidates(probabilities[label])


def test_thresholds_round_trip_through_metadata_artifact_and_json(tmp_path):
    frame = pd.DataFrame(
        {label: [0, 0, 1, 1] for label in MODELED_FAILURE_TYPE_COLUMNS}
    )
    probabilities = {
        label: np.asarray([0.1, 0.2, 0.7 + index * 0.01, 0.9])
        for index, label in enumerate(MODELED_FAILURE_TYPE_COLUMNS)
    }
    thresholds, _ = select_label_thresholds(frame, probabilities)
    metadata = artifact_metadata()
    metadata["thresholds"] = thresholds
    metadata_path = tmp_path / "metadata.json"
    write_metadata(metadata, metadata_path)
    reloaded_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    path, checksum = write_artifact(tmp_path, metadata=metadata)
    artifact = load_trusted_failure_type_artifact(
        path, expected_sha256=checksum, expected_metadata=metadata
    )
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        expected = select_threshold(frame[label], probabilities[label])
        assert metadata["thresholds"][label] == expected
        assert artifact["metadata"]["thresholds"][label] == expected
        assert reloaded_metadata["thresholds"][label] == expected


def test_predict_probabilities_uses_exact_integer_positive_class():
    frame = model_frame().iloc[:2]
    pipelines = {label: ReversedPipeline() for label in MODELED_FAILURE_TYPE_COLUMNS}
    probabilities = predict_probabilities(pipelines, frame)
    assert all(
        np.array_equal(values, np.asarray((0.7, 0.7)))
        for values in probabilities.values()
    )


@pytest.mark.parametrize(
    "pipeline",
    [NoPositivePipeline(), BooleanPositivePipeline(), DuplicatePositivePipeline()],
)
def test_predict_probabilities_rejects_invalid_positive_class(pipeline):
    pipelines = {label: pipeline for label in MODELED_FAILURE_TYPE_COLUMNS}
    with pytest.raises(FailureTypeModelingError):
        predict_probabilities(pipelines, model_frame().iloc[:1])


def test_multilabel_metrics_and_counts_are_correct():
    frame = pd.DataFrame(
        {
            "TWF": [1, 0, 0, 0],
            "HDF": [0, 1, 0, 0],
            "PWF": [0, 1, 0, 0],
            "OSF": [0, 0, 0, 1],
        }
    )
    probabilities = {
        "TWF": np.asarray([0.9, 0.1, 0.1, 0.1]),
        "HDF": np.asarray([0.1, 0.9, 0.1, 0.1]),
        "PWF": np.asarray([0.1, 0.9, 0.1, 0.1]),
        "OSF": np.asarray([0.1, 0.1, 0.1, 0.9]),
    }
    result = evaluate_failure_types(
        frame, probabilities, {label: 0.5 for label in MODELED_FAILURE_TYPE_COLUMNS}
    )
    assert result["aggregate"]["micro_f1"] == 1.0
    assert result["aggregate"]["hamming_loss"] == 0.0
    assert result["aggregate"]["subset_accuracy"] == 1.0
    assert result["aggregate"]["rows_with_no_predicted_label"] == 1
    assert result["aggregate"]["rows_with_any_predicted_label"] == 3
    assert result["aggregate"]["rows_with_multiple_predicted_labels"] == 1
    for metrics in result["per_label"].values():
        assert (
            sum(
                metrics[key]
                for key in (
                    "true_negative",
                    "false_positive",
                    "false_negative",
                    "true_positive",
                )
            )
            == 4
        )


def test_valid_artifact_and_checksum_before_deserialization(tmp_path, monkeypatch):
    path, checksum = write_artifact(tmp_path)
    loaded = load_trusted_failure_type_artifact(
        path, expected_sha256=checksum, expected_metadata=artifact_metadata()
    )
    assert tuple(loaded["pipelines"]) == MODELED_FAILURE_TYPE_COLUMNS
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(joblib, "load", forbidden)
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(path, expected_sha256="0" * 64)
    assert not called


@pytest.mark.parametrize(
    "mutation",
    [
        lambda metadata: metadata.update(model_version="bad"),
        lambda metadata: metadata.update(pipeline_version="bad"),
        lambda metadata: metadata.update(feature_columns=["urun_tipi"]),
        lambda metadata: metadata.update(target_labels=["TWF", "HDF", "PWF", "RNF"]),
        lambda metadata: metadata["thresholds"].update(RNF=0.5),
        lambda metadata: metadata["thresholds"].update(TWF=2.0),
    ],
)
def test_invalid_artifact_metadata_is_rejected(tmp_path, mutation):
    metadata = copy.deepcopy(artifact_metadata())
    mutation(metadata)
    path, checksum = write_artifact(tmp_path, metadata=metadata)
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(path, expected_sha256=checksum)


def test_invalid_pipeline_and_external_metadata_are_rejected(tmp_path):
    pipelines = {label: FakePipeline() for label in MODELED_FAILURE_TYPE_COLUMNS}
    pipelines.pop("OSF")
    path, checksum = write_artifact(tmp_path, pipelines=pipelines)
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(path, expected_sha256=checksum)
    pipelines["OSF"] = PredictOnlyPipeline()
    path, checksum = write_artifact(tmp_path, pipelines=pipelines)
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(path, expected_sha256=checksum)
    pipelines["OSF"] = NoPositivePipeline()
    path, checksum = write_artifact(tmp_path, pipelines=pipelines)
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(path, expected_sha256=checksum)
    path, checksum = write_artifact(tmp_path)
    external = artifact_metadata()
    external["thresholds"]["TWF"] = 0.4
    with pytest.raises(ArtifactValidationError):
        load_trusted_failure_type_artifact(
            path, expected_sha256=checksum, expected_metadata=external
        )


def test_metadata_rejects_nan_and_contains_no_raw_records(tmp_path):
    path = tmp_path / "metadata.json"
    with pytest.raises(ValueError):
        write_metadata({"metric": float("nan")}, path)
    metadata = artifact_metadata()
    write_metadata(metadata, path)
    serialized = path.read_text(encoding="utf-8")
    assert "sensor_rows" not in serialized and "records" not in serialized
