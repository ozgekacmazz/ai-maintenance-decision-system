import json
import os
import subprocess
import sys

import pandas as pd
import pytest

from bakim_ml.data_contract import (
    FAILURE_TYPE_COLUMNS,
    MODEL_FEATURE_COLUMNS,
)
from bakim_ml.failure_labels import (
    FailureLabelAnalysisError,
    analyze_failure_labels,
    build_analysis_metadata,
    write_analysis_metadata,
)
from bakim_ml.features import add_engineered_features, add_replay_fields
from bakim_ml.loaders import (
    REPO_ROOT,
    DatasetLoadError,
    file_sha256,
    load_prepared_dataset,
)


def analysis_frame():
    rows = [
        [1, "L00001", "L", 298.1, 308.6, 1551, 42.8, 0, 0, 0, 0, 0, 0, 0],
        [2, "L00002", "L", 298.2, 308.7, 1500, 40.0, 5, 1, 1, 0, 0, 0, 0],
        [3, "M00003", "M", 299.0, 309.0, 1400, 50.0, 20, 1, 0, 1, 1, 0, 0],
        [4, "H00004", "H", 300.0, 310.0, 1450, 45.0, 30, 0, 0, 0, 0, 0, 1],
        [5, "L00005", "L", 301.0, 311.0, 1600, 35.0, 40, 1, 0, 0, 0, 1, 0],
    ]
    columns = (
        "udi",
        "urun_kodu",
        "urun_tipi",
        "hava_sicakligi_k",
        "proses_sicakligi_k",
        "donus_hizi_rpm",
        "tork_nm",
        "takim_asinmasi_dk",
        "makine_arizasi",
        *FAILURE_TYPE_COLUMNS,
    )
    base = pd.DataFrame(rows, columns=columns)
    frame = pd.concat([base] * 20, ignore_index=True)
    frame["udi"] = range(1, len(frame) + 1)
    return frame


def prepared_frame():
    return add_replay_fields(add_engineered_features(analysis_frame()))


def test_label_counts_rows_and_combinations_are_correct_and_deterministic():
    first = analyze_failure_labels(analysis_frame())
    second = analyze_failure_labels(analysis_frame())
    assert first == second
    assert first["label_counts"] == {
        "TWF": {"positive": 20, "negative": 80},
        "HDF": {"positive": 20, "negative": 80},
        "PWF": {"positive": 20, "negative": 80},
        "OSF": {"positive": 20, "negative": 80},
        "RNF": {"positive": 20, "negative": 80},
    }
    assert first["rows_with_no_label"] == 20
    assert first["rows_with_single_label"] == 60
    assert first["rows_with_multiple_labels"] == 20
    assert list(first["label_combinations"]) == [
        "NONE",
        "TWF",
        "OSF",
        "RNF",
        "HDF+PWF",
    ]


def test_pairwise_consistency_rnf_cardinality_and_density():
    result = analyze_failure_labels(analysis_frame())
    assert result["pairwise_cooccurrence"]["HDF+PWF"] == 20
    assert sum(result["pairwise_cooccurrence"].values()) == 20
    assert result["machine_failure_consistency"] == {
        "machine_failure_0_no_type": 20,
        "machine_failure_1_with_type": 60,
        "machine_failure_1_no_type": 0,
        "machine_failure_0_with_type": 20,
        "multiple_types_machine_failure_1": 20,
        "multiple_types_machine_failure_0": 0,
    }
    assert result["rnf_analysis"] == {
        "positive": 20,
        "machine_failure_0": 20,
        "machine_failure_1": 0,
        "with_other_failure_type": 0,
    }
    assert result["label_cardinality"] == pytest.approx(1.0)
    assert result["label_density"] == pytest.approx(0.2)


def test_split_statistics_are_deterministic_disjoint_and_complete():
    first = analyze_failure_labels(analysis_frame())["split"]
    second = analyze_failure_labels(analysis_frame())["split"]
    assert first == second
    assert [first[name]["rows"] for name in ("train", "validation", "test")] == [
        70,
        15,
        15,
    ]
    assert first["contract"] == {
        "random_seed": 42,
        "strategy": "binary_machine_failure_stratified_70_15_15",
        "all_rows_once": True,
    }
    for name in ("train", "validation", "test"):
        assert set(first[name]["label_positive_counts"]) == set(FAILURE_TYPE_COLUMNS)


def test_metadata_is_safe_native_deterministic_and_has_no_raw_rows(tmp_path):
    frame = analysis_frame()
    original = frame.copy(deep=True)
    first = build_analysis_metadata(
        frame,
        source_sha256="a" * 64,
        prepared_source_sha256="b" * 64,
        created_at="2026-01-01T00:00:00+00:00",
    )
    second = build_analysis_metadata(
        frame,
        source_sha256="a" * 64,
        prepared_source_sha256="b" * 64,
        created_at="2027-01-01T00:00:00+00:00",
    )
    assert first["analysis_fingerprint_sha256"] == second["analysis_fingerprint_sha256"]
    assert first["source_sha256"] == "a" * 64
    assert first["prepared_source_sha256"] == "b" * 64
    assert not set(FAILURE_TYPE_COLUMNS) & set(MODEL_FEATURE_COLUMNS)
    assert "makine_arizasi" not in MODEL_FEATURE_COLUMNS
    path = tmp_path / "analysis.json"
    write_analysis_metadata(first, path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["total_rows"] == 100
    assert "records" not in loaded and "sensor_rows" not in loaded
    assert "NaN" not in path.read_text(encoding="utf-8")
    assert "Infinity" not in path.read_text(encoding="utf-8")
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("value", [2, -1, 0.5])
def test_non_binary_label_is_rejected(value):
    frame = analysis_frame()
    frame["TWF"] = frame["TWF"].astype(object)
    frame.loc[0, "TWF"] = value
    with pytest.raises(FailureLabelAnalysisError):
        analyze_failure_labels(frame)


def test_missing_label_and_empty_data_are_rejected():
    frame = analysis_frame()
    with pytest.raises(FailureLabelAnalysisError):
        analyze_failure_labels(frame.drop(columns="RNF"))
    with pytest.raises(FailureLabelAnalysisError):
        analyze_failure_labels(frame.iloc[0:0])


def test_prepared_loader_checksum_and_cli_repeatability(tmp_path):
    prepared = prepared_frame()
    input_path = tmp_path / "prepared.csv"
    prepared.to_csv(input_path, index=False)
    checksum = file_sha256(input_path)
    loaded = load_prepared_dataset(input_path, expected_sha256=checksum)
    assert len(loaded) == len(prepared)
    with pytest.raises(DatasetLoadError):
        load_prepared_dataset(input_path, expected_sha256="0" * 64)

    metadata_path = tmp_path / "prepared.json"
    metadata_path.write_text(json.dumps({"source_sha256": "a" * 64}), encoding="utf-8")
    first_output = tmp_path / "first.json"
    second_output = tmp_path / "second.json"
    command = [
        sys.executable,
        str(REPO_ROOT / "ml" / "scripts" / "analyze_failure_labels.py"),
        "--input",
        str(input_path),
        "--prepared-metadata",
        str(metadata_path),
        "--expected-sha256",
        checksum,
    ]
    subprocess.run(
        [
            *command,
            "--output",
            str(first_output),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "ml" / "src")},
    )
    subprocess.run(
        [
            *command,
            "--output",
            str(second_output),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "ml" / "src")},
    )
    first = json.loads(first_output.read_text(encoding="utf-8"))
    second = json.loads(second_output.read_text(encoding="utf-8"))
    assert first["analysis_fingerprint_sha256"] == second["analysis_fingerprint_sha256"]
