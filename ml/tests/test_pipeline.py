import json

import numpy as np
import pandas as pd
import pytest

from bakim_ml.data_contract import (
    BINARY_TARGET_COLUMNS,
    ID_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    canonicalize_columns,
)
from bakim_ml.features import ReplayConfig, add_engineered_features, add_replay_fields
from bakim_ml.loaders import DatasetLoadError, file_sha256, load_dataset
from bakim_ml.prepare import prepare_dataset
from bakim_ml.validation import validate_quality


def write_csv(frame, path):
    frame.to_csv(path, index=False)
    return path


def test_contract_mapping_and_leakage(raw_frame):
    canonical = canonicalize_columns(raw_frame)
    assert list(canonicalize_columns(raw_frame).columns) == list(canonical.columns)
    assert not set(BINARY_TARGET_COLUMNS + ID_COLUMNS) & set(MODEL_FEATURE_COLUMNS)


def test_loader_valid_missing_numeric_binary_and_checksum(
    raw_frame, tmp_path, monkeypatch
):
    valid = write_csv(raw_frame, tmp_path / "valid.csv")
    assert len(load_dataset(valid, expected_sha256=file_sha256(valid))) == 2
    with pytest.raises(DatasetLoadError):
        load_dataset(tmp_path / "missing.csv")
    bad = raw_frame.copy()
    bad["Torque [Nm]"] = bad["Torque [Nm]"].astype(object)
    bad.loc[0, "Torque [Nm]"] = "bad"
    with pytest.raises(DatasetLoadError):
        load_dataset(write_csv(bad, tmp_path / "numeric.csv"))
    bad = raw_frame.copy()
    bad.loc[0, "TWF"] = 2
    with pytest.raises(DatasetLoadError):
        load_dataset(write_csv(bad, tmp_path / "binary.csv"))
    with pytest.raises(DatasetLoadError):
        load_dataset(valid, expected_sha256="0" * 64)
    monkeypatch.chdir(tmp_path)
    assert len(load_dataset(valid)) == 2


@pytest.mark.parametrize(
    ("column", "value", "code"),
    [
        ("urun_tipi", "X", "UNKNOWN_PRODUCT_TYPE"),
        ("tork_nm", -1, "INVALID_TORQUE"),
        ("takim_asinmasi_dk", -1, "INVALID_TOOL_WEAR"),
        ("donus_hizi_rpm", 0, "INVALID_ROTATIONAL_SPEED"),
        ("hava_sicakligi_k", 0, "INVALID_AIR_TEMPERATURE"),
    ],
)
def test_quality_errors(raw_frame, column, value, code):
    frame = canonicalize_columns(raw_frame)
    frame.loc[0, column] = value
    result = validate_quality(frame)
    assert not result.passed and code in {issue.code for issue in result.issues}


def test_quality_null_duplicate_anomalies_and_empty(raw_frame):
    frame = canonicalize_columns(raw_frame)
    frame.loc[0, "tork_nm"] = np.nan
    frame.loc[1, "udi"] = frame.loc[0, "udi"]
    codes = {issue.code for issue in validate_quality(frame).issues}
    assert {"NULL_VALUES", "DUPLICATE_UDI"} <= codes
    anomaly = canonicalize_columns(raw_frame)
    anomaly.loc[0, "RNF"] = 1
    result = validate_quality(anomaly)
    assert result.passed and "FAILURE_TYPE_WITHOUT_FAILURE" in {
        i.code for i in result.issues
    }
    assert not validate_quality(frame.iloc[0:0]).passed


def test_features_are_correct_finite_deterministic_and_non_mutating(raw_frame):
    frame = canonicalize_columns(raw_frame)
    original = frame.copy(deep=True)
    result = add_engineered_features(frame)
    assert result.loc[0, "proses_hava_sicaklik_farki_k"] == pytest.approx(10.5)
    assert result.loc[0, "mekanik_guc_w"] == pytest.approx(42.8 * 2 * np.pi * 1551 / 60)
    pd.testing.assert_frame_equal(frame, original)
    broken = frame.copy()
    broken.loc[0, "tork_nm"] = np.inf
    with pytest.raises(ValueError):
        add_engineered_features(broken)


def test_replay_defaults_config_determinism_and_order(raw_frame):
    frame = pd.concat([canonicalize_columns(raw_frame)] * 21, ignore_index=True)
    first = add_replay_fields(frame)
    second = add_replay_fields(frame)
    pd.testing.assert_frame_equal(first, second)
    assert first["machine_id"].nunique() == 20
    assert str(first["timestamp"].dt.tz) == "UTC"
    custom = add_replay_fields(
        frame, ReplayConfig(machine_count=3, interval_minutes=10)
    )
    assert custom["machine_id"].nunique() == 3
    assert all(
        group["timestamp"].is_monotonic_increasing
        for _, group in custom.groupby("machine_id")
    )


def test_prepare_preserves_source_rows_metadata_and_no_index(raw_frame, tmp_path):
    source = write_csv(raw_frame, tmp_path / "raw.csv")
    before = file_sha256(source)
    output = tmp_path / "processed" / "prepared.csv"
    metadata = tmp_path / "meta.json"
    prepared, document = prepare_dataset(source, output, metadata)
    assert file_sha256(source) == before and len(prepared) == len(raw_frame)
    loaded = pd.read_csv(output)
    assert "Unnamed: 0" not in loaded.columns
    assert json.loads(metadata.read_text(encoding="utf-8"))["rows"] == 2
    assert document["source"] == "data/raw/ai4i2020.csv"
    assert not output.with_suffix(".csv.tmp").exists()
