import copy
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import shap
import sklearn
from sklearn.ensemble import RandomForestClassifier

from bakim_ml.artifact import load_trusted_artifact, load_trusted_failure_type_artifact
from bakim_ml.data_contract import MODELED_FAILURE_TYPE_COLUMNS
from bakim_ml.explainability import (
    ExplainabilityError,
    _explain_pipeline,
    explain_binary_prediction,
    explain_failure_type_prediction,
    normalize_positive_class_shap_values,
    positive_class_index,
)
from bakim_ml.loaders import REPO_ROOT, load_prepared_dataset
from bakim_ml.shap_report import (
    _select_validation_sample,
    deterministic_fingerprint,
    generate_shap_analysis,
)


class IdentityPreprocessor:
    def transform(self, frame):
        return np.asarray([[1.0, 2.0, 3.0]])

    def get_feature_names_out(self):
        return np.asarray(("b_feature", "a_feature", "c_feature"))


class FakePipeline:
    def __init__(self, probability=0.5):
        estimator = RandomForestClassifier(n_estimators=1, random_state=42).fit(
            [[0.0], [1.0]], [0, 1]
        )
        self.named_steps = {
            "preprocessor": IdentityPreprocessor(),
            "model": estimator,
        }
        self.probability = probability

    def predict_proba(self, frame):
        return np.asarray([[1 - self.probability, self.probability]])


class FakeExplainer:
    def __init__(self, estimator, *, values=None, base_values=None):
        self.values = values
        self.base_values = base_values

    def __call__(self, transformed, check_additivity=False):
        values = self.values
        if values is None:
            values = np.asarray([[[0.0, 0.2], [0.0, -0.2], [0.0, 0.0]]])
        base_values = self.base_values
        if base_values is None:
            base_values = np.asarray([[0.5, 0.5]])
        return shap.Explanation(
            values=values,
            base_values=base_values,
            data=transformed,
        )


def sensor():
    return {
        "urun_tipi": "L",
        "hava_sicakligi_k": 298.1,
        "proses_sicakligi_k": 308.6,
        "donus_hizi_rpm": 1551.0,
        "tork_nm": 42.8,
        "takim_asinmasi_dk": 0.0,
        "udi": 1,
        "makine_arizasi": 1,
        "RNF": 1,
    }


@pytest.mark.parametrize(
    ("classes", "expected"),
    [((1, 0), 0), ((0, 1), 1)],
)
def test_positive_class_index_supports_reversed_order(classes, expected):
    assert positive_class_index(np.asarray(classes)) == expected


@pytest.mark.parametrize("classes", [(0, 2), (False, True), (0, 1, 1)])
def test_positive_class_index_rejects_invalid_contract(classes):
    with pytest.raises(ExplainabilityError):
        positive_class_index(np.asarray(classes))


@pytest.mark.parametrize(
    "output",
    [
        [np.asarray([[1.0, 2.0, 3.0]]), np.asarray([[4.0, 5.0, 6.0]])],
        np.asarray([[[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]]),
        shap.Explanation(
            values=np.asarray([[[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]]),
            base_values=np.asarray([[0.8, 0.2]]),
        ),
    ],
)
def test_supported_shap_shapes_normalize_to_positive_vector(output):
    normalized = normalize_positive_class_shap_values(
        output,
        positive_index=1,
        feature_count=3,
        base_values=np.asarray((0.8, 0.2)),
    )
    assert np.array_equal(normalized.values, np.asarray((4.0, 5.0, 6.0)))
    assert normalized.base_value == 0.2


def test_2d_single_row_is_already_class_selected_and_has_no_class_axis():
    # (1, feature_count) tek-output sözleşmesidir; sınıf ekseni içermez.
    normalized = normalize_positive_class_shap_values(
        np.asarray([[4.0, 5.0, 6.0]]),
        positive_index=1,
        feature_count=3,
        base_values=0.2,
    )
    assert np.array_equal(normalized.values, np.asarray((4.0, 5.0, 6.0)))
    assert normalized.base_value == 0.2


@pytest.mark.parametrize(
    "output",
    [np.zeros((2, 3, 2)), np.zeros((2, 2)), np.zeros((1, 2, 2, 2))],
)
def test_unexpected_shap_shape_is_rejected(output):
    with pytest.raises(ExplainabilityError):
        normalize_positive_class_shap_values(
            output,
            positive_index=1,
            feature_count=3,
            base_values=(0.8, 0.2),
        )


def test_shap_feature_count_mismatch_is_rejected():
    with pytest.raises(ExplainabilityError):
        normalize_positive_class_shap_values(
            np.asarray((1.0, 2.0)),
            positive_index=1,
            feature_count=3,
            base_values=(0.8, 0.2),
        )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf")])
def test_non_finite_shap_and_base_values_are_rejected(invalid):
    with pytest.raises(ExplainabilityError):
        normalize_positive_class_shap_values(
            np.asarray((1.0, invalid, 2.0)),
            positive_index=1,
            feature_count=3,
            base_values=(0.8, 0.2),
        )
    with pytest.raises(ExplainabilityError):
        normalize_positive_class_shap_values(
            np.asarray((1.0, 0.0, 2.0)),
            positive_index=1,
            feature_count=3,
            base_values=(0.8, invalid),
        )


def test_contributions_are_deterministic_and_input_is_not_mutated(monkeypatch):
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    payload = sensor()
    original = copy.deepcopy(payload)
    result = _explain_pipeline(FakePipeline(), payload, "machine_failure", top_n=3)
    assert [item["feature"] for item in result["feature_contributions"]] == [
        "a_feature",
        "b_feature",
        "c_feature",
    ]
    assert [item["direction"] for item in result["feature_contributions"]] == [
        "RISKI_AZALTIR",
        "RISKI_ARTIRIR",
        "NOTR",
    ]
    assert payload == original
    serialized = json.dumps(result)
    assert all(name not in serialized for name in ("udi", "makine_arizasi", "RNF"))


@pytest.mark.parametrize("top_n", [-1, True, 1.5, 4])
def test_invalid_top_n_is_rejected(monkeypatch, top_n):
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    with pytest.raises(ExplainabilityError):
        _explain_pipeline(FakePipeline(), sensor(), "machine_failure", top_n=top_n)


def test_top_n_filters_only_display_after_full_additivity(monkeypatch):
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    result = _explain_pipeline(FakePipeline(), sensor(), "machine_failure", top_n=1)
    assert len(result["feature_contributions"]) == 1
    assert result["predicted_probability"] == pytest.approx(
        result["base_value"] + 0.2 - 0.2
    )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf")])
def test_non_finite_transformed_feature_is_rejected(monkeypatch, invalid):
    pipeline = FakePipeline()
    pipeline.named_steps["preprocessor"].transform = lambda frame: np.asarray(
        [[1.0, invalid, 3.0]]
    )
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    with pytest.raises(ExplainabilityError):
        _explain_pipeline(pipeline, sensor(), "machine_failure", top_n=3)


def test_dataframe_input_is_not_mutated(monkeypatch):
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    frame = pd.DataFrame([sensor()])
    original = frame.copy(deep=True)
    _explain_pipeline(FakePipeline(), frame, "machine_failure", top_n=3)
    pd.testing.assert_frame_equal(frame, original)


def test_broken_additivity_is_rejected(monkeypatch):
    class BrokenExplainer(FakeExplainer):
        def __call__(self, transformed, check_additivity=False):
            return shap.Explanation(
                values=np.asarray([[[0.0, 0.4], [0.0, 0.3], [0.0, 0.2]]]),
                base_values=np.asarray([[0.5, 0.5]]),
            )

    monkeypatch.setattr(shap, "TreeExplainer", BrokenExplainer)
    with pytest.raises(ExplainabilityError):
        _explain_pipeline(FakePipeline(), sensor(), "machine_failure", top_n=3)


def test_failure_type_explanation_is_mathematical_and_has_no_serving_policy(
    monkeypatch,
):
    monkeypatch.setattr(shap, "TreeExplainer", FakeExplainer)
    artifact = {
        "metadata": {"target_labels": list(MODELED_FAILURE_TYPE_COLUMNS)},
        "pipelines": {label: FakePipeline() for label in MODELED_FAILURE_TYPE_COLUMNS},
    }
    twf = explain_failure_type_prediction(artifact, sensor(), "TWF", top_n=2)
    assert "guven_durumu" not in twf
    assert "operasyonel_kullanima_uygun" not in twf
    assert "guven_durumu" not in explain_failure_type_prediction(
        artifact, sensor(), "HDF", top_n=2
    )
    for label in ("RNF", "UNKNOWN"):
        with pytest.raises(ExplainabilityError):
            explain_failure_type_prediction(artifact, sensor(), label, top_n=2)


def test_fingerprint_ignores_created_at_and_is_deterministic():
    first = {"created_at": "one", "value": 1.0, "nested": {"b": 2}}
    second = {"nested": {"b": 2}, "value": 1.0, "created_at": "two"}
    assert deterministic_fingerprint(first) == deterministic_fingerprint(second)


def test_validation_sample_is_seeded_unique_subset_not_sorted_head():
    validation = pd.DataFrame(
        {"value": range(20)},
        index=pd.Index(range(100, 120), name="source_index"),
    )
    first = _select_validation_sample(validation, 7, random_seed=42)
    second = _select_validation_sample(validation, 7, random_seed=42)

    assert first.index.tolist() == second.index.tolist()
    assert len(first) == 7
    assert first.index.is_unique
    assert set(first.index).issubset(validation.index)
    assert first.index.tolist() != validation.sort_index().head(7).index.tolist()


def test_validation_sample_rejects_size_above_validation_count():
    validation = pd.DataFrame({"value": range(3)})
    with pytest.raises(ValueError, match="validation split boyutunu aşamaz"):
        _select_validation_sample(validation, 4)


ARTIFACTS_AVAILABLE = all(
    (REPO_ROOT / path).is_file()
    for path in (
        "ml/artifacts/binary-failure-1.0.0.joblib",
        "ml/artifacts/failure-type-1.0.0.joblib",
    )
)


@pytest.fixture(scope="module")
def real_artifacts():
    binary_metadata = json.loads(
        (REPO_ROOT / "data/metadata/binary_failure_model.json").read_text(
            encoding="utf-8"
        )
    )
    failure_metadata = json.loads(
        (REPO_ROOT / "data/metadata/failure_type_model.json").read_text(
            encoding="utf-8"
        )
    )
    binary = load_trusted_artifact(
        REPO_ROOT / binary_metadata["artifact"]["relative_path"],
        expected_sha256=binary_metadata["artifact"]["sha256"],
    )
    failure = load_trusted_failure_type_artifact(
        REPO_ROOT / failure_metadata["artifact"]["relative_path"],
        expected_sha256=failure_metadata["artifact"]["sha256"],
        expected_metadata=failure_metadata,
    )
    return binary, failure


def test_runtime_sklearn_exactly_matches_both_tracked_metadata_versions():
    tracked_paths = (
        REPO_ROOT / "data/metadata/binary_failure_model.json",
        REPO_ROOT / "data/metadata/failure_type_model.json",
    )
    tracked_versions = {
        json.loads(path.read_text(encoding="utf-8"))["runtime"]["scikit_learn"]
        for path in tracked_paths
    }
    assert tracked_versions == {sklearn.__version__}


@pytest.mark.skipif(not ARTIFACTS_AVAILABLE, reason="Yerel artefaktlar mevcut değil.")
def test_runtime_sklearn_matches_tracked_and_artifact_training_versions(
    real_artifacts,
):
    binary, failure = real_artifacts
    tracked_versions = {
        json.loads(path.read_text(encoding="utf-8"))["runtime"]["scikit_learn"]
        for path in (
            REPO_ROOT / "data/metadata/binary_failure_model.json",
            REPO_ROOT / "data/metadata/failure_type_model.json",
        )
    }
    artifact_versions = {
        artifact["metadata"]["runtime"]["scikit_learn"]
        for artifact in (binary, failure)
    }
    assert tracked_versions == artifact_versions == {sklearn.__version__}


@pytest.mark.skipif(not ARTIFACTS_AVAILABLE, reason="Yerel artefaktlar mevcut değil.")
def test_real_artifacts_explain_positive_classes_with_finite_additivity(real_artifacts):
    binary, failure = real_artifacts
    row = load_prepared_dataset().iloc[0]
    explanations = [explain_binary_prediction(binary, row, top_n=11)]
    explanations.extend(
        explain_failure_type_prediction(failure, row, label, top_n=11)
        for label in MODELED_FAILURE_TYPE_COLUMNS
    )
    assert explanations[0]["target"] == "machine_failure"
    assert "guven_durumu" not in explanations[1]
    for explanation in explanations:
        assert np.isfinite(explanation["predicted_probability"])
        assert np.isfinite(explanation["base_value"])
        assert all(
            np.isfinite(item["feature_value"]) and np.isfinite(item["shap_value"])
            for item in explanation["feature_contributions"]
        )
    with pytest.raises(ExplainabilityError):
        explain_failure_type_prediction(failure, row, "RNF")


@pytest.mark.skipif(not ARTIFACTS_AVAILABLE, reason="Yerel artefaktlar mevcut değil.")
def test_global_report_is_finite_aggregate_only_and_deterministic(tmp_path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first = generate_shap_analysis(sample_size=2, output_path=first_path)
    second = generate_shap_analysis(sample_size=2, output_path=second_path)
    assert first["fingerprint"] == second["fingerprint"]
    serialized = first_path.read_text(encoding="utf-8")
    parsed = json.loads(serialized)
    assert "sensor_rows" not in parsed and "records" not in parsed
    assert "urun_kodu" not in serialized and "machine_id" not in serialized
    assert parsed["sample"]["size"] == 2


@pytest.mark.skipif(not ARTIFACTS_AVAILABLE, reason="Yerel artefaktlar mevcut değil.")
def test_shap_report_cli_twice_has_same_safe_fingerprint(tmp_path):
    outputs = (tmp_path / "first.json", tmp_path / "second.json")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT / "ml/src")
    script = REPO_ROOT / "ml/scripts/generate_shap_report.py"
    documents = []

    for output in outputs:
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--sample-size",
                "2",
                "--output",
                str(output),
            ],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
        serialized = output.read_text(encoding="utf-8")
        assert "NaN" not in serialized and "Infinity" not in serialized
        assert all(
            raw_key not in serialized
            for raw_key in ("sensor_rows", "records", "urun_kodu", "machine_id")
        )
        documents.append(json.loads(serialized))

    assert documents[0]["fingerprint"] == documents[1]["fingerprint"]
