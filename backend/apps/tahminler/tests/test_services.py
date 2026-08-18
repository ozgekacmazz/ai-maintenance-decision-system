import copy
import json
from hashlib import sha256

import joblib
import numpy as np
import pytest
from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from bakim_ml.features import add_engineered_features

from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.services import (
    MODEL_VERSION,
    YukluModel,
    model_cache_sifirla,
    modeli_getir,
    risk_tahmini_yap,
)


class FakePipeline:
    def __init__(self, probability=0.8, classes=(0, 1)):
        self.probability = probability
        self.classes_ = np.asarray(classes)
        self.calls = 0

    def predict_proba(self, frame):
        self.calls += 1
        return np.asarray([[1 - self.probability, self.probability]])


class PredictOnlyPipeline:
    classes_ = np.asarray((0, 1))

    def predict(self, frame):
        return np.asarray((0,))


class BrokenPipeline(FakePipeline):
    def predict_proba(self, frame):
        raise RuntimeError("internal model detail")


@pytest.fixture(autouse=True)
def clean_model_cache():
    model_cache_sifirla()
    yield
    model_cache_sifirla()


def sensor():
    return {
        "urun_tipi": "L",
        "hava_sicakligi_k": 298.1,
        "proses_sicakligi_k": 308.6,
        "donus_hizi_rpm": 1551.0,
        "tork_nm": 42.8,
        "takim_asinmasi_dk": 0.0,
    }


def artifact_files(
    tmp_path, *, pipeline=None, metadata_changes=None, artifact_changes=None
):
    metadata = {
        "model_version": MODEL_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "feature_columns": list(MODEL_FEATURE_COLUMNS),
        "threshold": 0.6,
    }
    metadata.update(metadata_changes or {})
    artifact_metadata = copy.deepcopy(metadata)
    artifact_metadata.update(artifact_changes or {})
    artifact_path = tmp_path / "model.joblib"
    joblib.dump(
        {"pipeline": pipeline or FakePipeline(), "metadata": artifact_metadata},
        artifact_path,
    )
    checksum = sha256(artifact_path.read_bytes()).hexdigest()
    metadata["artifact"] = {"sha256": checksum}
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return artifact_path, metadata_path


def test_valid_artifact_loads_and_cache_loads_once(tmp_path, monkeypatch):
    paths = artifact_files(tmp_path)
    calls = 0
    import apps.tahminler.services as services

    real_loader = services._model_yukle

    def counted_loader(*args):
        nonlocal calls
        calls += 1
        return real_loader(*args)

    monkeypatch.setattr(services, "_model_yukle", counted_loader)
    first = modeli_getir(artifact_path=paths[0], metadata_path=paths[1])
    second = modeli_getir(artifact_path=paths[0], metadata_path=paths[1])
    assert first is second
    assert calls == 1


def test_checksum_mismatch_is_rejected_before_joblib_load(tmp_path, monkeypatch):
    artifact_path, metadata_path = artifact_files(tmp_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["artifact"]["sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    called = False

    def forbidden_load(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(joblib, "load", forbidden_load)
    with pytest.raises(ModelHizmetiHatasi):
        modeli_getir(artifact_path=artifact_path, metadata_path=metadata_path)
    assert not called


@pytest.mark.parametrize("missing", ["artifact", "metadata"])
def test_missing_file_is_controlled(tmp_path, missing):
    artifact_path, metadata_path = artifact_files(tmp_path)
    (artifact_path if missing == "artifact" else metadata_path).unlink()
    with pytest.raises(ModelHizmetiHatasi):
        modeli_getir(artifact_path=artifact_path, metadata_path=metadata_path)


@pytest.mark.parametrize(
    "changes",
    [
        {"pipeline_version": "9.0.0"},
        {"feature_columns": ["urun_tipi"]},
        {"threshold": 1.1},
    ],
)
def test_invalid_metadata_contract_is_rejected(tmp_path, changes):
    paths = artifact_files(tmp_path, metadata_changes=changes)
    with pytest.raises(ModelHizmetiHatasi):
        modeli_getir(artifact_path=paths[0], metadata_path=paths[1])


def test_pipeline_without_predict_proba_is_rejected(tmp_path):
    paths = artifact_files(tmp_path, pipeline=PredictOnlyPipeline())
    with pytest.raises(ModelHizmetiHatasi):
        modeli_getir(artifact_path=paths[0], metadata_path=paths[1])


def test_missing_positive_class_is_rejected(tmp_path):
    paths = artifact_files(tmp_path, pipeline=FakePipeline(classes=(0, 2)))
    with pytest.raises(ModelHizmetiHatasi):
        modeli_getir(artifact_path=paths[0], metadata_path=paths[1])


def test_cache_reset_forces_reload(tmp_path):
    paths = artifact_files(tmp_path)
    first = modeli_getir(artifact_path=paths[0], metadata_path=paths[1])
    model_cache_sifirla()
    second = modeli_getir(artifact_path=paths[0], metadata_path=paths[1])
    assert first is not second


def test_inference_reuses_training_features_without_mutating_input():
    payload = sensor()
    original = copy.deepcopy(payload)
    pipeline = FakePipeline(probability=0.7)
    model = YukluModel(pipeline, 0.6, MODEL_VERSION, PIPELINE_VERSION)
    result = risk_tahmini_yap(payload, model=model)
    expected = add_engineered_features(__import__("pandas").DataFrame([payload]))
    assert expected.loc[0, "proses_hava_sicaklik_farki_k"] == pytest.approx(10.5)
    assert expected.loc[0, "acisal_hiz_rad_s"] == pytest.approx(2 * np.pi * 1551 / 60)
    assert expected.loc[0, "mekanik_guc_w"] == pytest.approx(
        42.8 * 2 * np.pi * 1551 / 60
    )
    assert payload == original
    assert result["risk_orani"] == 0.7
    assert result["risk_uyarisi"] is True


def test_inference_runtime_failure_is_controlled():
    model = YukluModel(BrokenPipeline(), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    with pytest.raises(ModelHizmetiHatasi):
        risk_tahmini_yap(sensor(), model=model)
