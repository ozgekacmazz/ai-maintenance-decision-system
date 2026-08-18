import copy
import json
import threading
from hashlib import sha256

import joblib
import numpy as np
import pytest
from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from bakim_ml.features import add_engineered_features

from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.services import (
    FAILURE_TYPE_MODEL_VERSION,
    MODEL_VERSION,
    YukluArizaTipiModeli,
    YukluModel,
    ariza_tipi_model_cache_sifirla,
    ariza_tipi_modeli_getir,
    binary_model_cache_sifirla,
    hiyerarsik_risk_tahmini_yap,
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


class BadShapePipeline(FakePipeline):
    def predict_proba(self, frame):
        return np.asarray([self.probability])


def failure_type_model(probabilities=None):
    probabilities = probabilities or {"TWF": 0.1, "HDF": 0.8, "PWF": 0.7, "OSF": 0.2}
    return YukluArizaTipiModeli(
        pipelines={
            label: FakePipeline(value) for label, value in probabilities.items()
        },
        thresholds={"TWF": 0.051, "HDF": 0.2, "PWF": 0.3, "OSF": 0.25},
        model_version=FAILURE_TYPE_MODEL_VERSION,
        pipeline_version=PIPELINE_VERSION,
    )


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


def test_low_risk_does_not_load_or_run_failure_type(monkeypatch):
    binary = YukluModel(FakePipeline(0.1), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    monkeypatch.setattr(
        "apps.tahminler.services.ariza_tipi_modeli_getir",
        lambda: pytest.fail("Failure-type yüklenmemeliydi"),
    )
    result = hiyerarsik_risk_tahmini_yap(sensor(), binary_model=binary)
    assert result["ariza_tipi_degerlendirmesi"] == {
        "durum": "RISK_ESIK_ALTINDA",
        "guvenilir_adaylar": [],
        "deneysel_sinyaller": [],
        "belirsiz_fiziksel_tip": False,
    }


def test_hierarchical_prediction_prepares_features_once_without_mutating_input(
    monkeypatch,
):
    import apps.tahminler.services as services

    payload = sensor()
    original = copy.deepcopy(payload)
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model()
    real_prepare = services._ozellikleri_hazirla
    calls = 0

    def counted_prepare(sensor_verisi):
        nonlocal calls
        calls += 1
        return real_prepare(sensor_verisi)

    monkeypatch.setattr(services, "_ozellikleri_hazirla", counted_prepare)
    result = hiyerarsik_risk_tahmini_yap(
        payload, binary_model=binary, failure_type_model=failure
    )

    assert result["risk_uyarisi"] is True
    assert result["ariza_tipi_degerlendirmesi"]["durum"] == "DEGERLENDIRILDI"
    assert binary.pipeline.calls == 1
    assert all(pipeline.calls == 1 for pipeline in failure.pipelines.values())
    assert calls == 1
    assert payload == original


def test_high_risk_runs_all_four_types_and_applies_policy():
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model()
    result = hiyerarsik_risk_tahmini_yap(
        sensor(), binary_model=binary, failure_type_model=failure
    )["ariza_tipi_degerlendirmesi"]
    assert [item["kod"] for item in result["guvenilir_adaylar"]] == ["HDF", "PWF"]
    assert all(pipeline.calls == 1 for pipeline in failure.pipelines.values())
    twf = result["deneysel_sinyaller"][0]
    assert twf == {
        "kod": "TWF",
        "olasilik": 0.1,
        "threshold": 0.051,
        "esik_asildi": True,
        "guven_durumu": "YETERSIZ_DESTEK",
        "operasyonel_kullanima_uygun": False,
    }
    assert "RNF" not in str(result)
    assert result["belirsiz_fiziksel_tip"] is False


def test_equal_trusted_probabilities_follow_central_policy_order():
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model({"TWF": 0.8, "HDF": 0.9, "PWF": 0.9, "OSF": 0.9})
    result = hiyerarsik_risk_tahmini_yap(
        sensor(), binary_model=binary, failure_type_model=failure
    )["ariza_tipi_degerlendirmesi"]

    assert [item["kod"] for item in result["guvenilir_adaylar"]] == [
        "HDF",
        "PWF",
        "OSF",
    ]
    assert [item["kod"] for item in result["deneysel_sinyaller"]] == ["TWF"]


def test_only_twf_above_threshold_remains_uncertain():
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model({"TWF": 0.8, "HDF": 0.1, "PWF": 0.1, "OSF": 0.1})
    result = hiyerarsik_risk_tahmini_yap(
        sensor(), binary_model=binary, failure_type_model=failure
    )["ariza_tipi_degerlendirmesi"]
    assert result["guvenilir_adaylar"] == []
    assert result["deneysel_sinyaller"][0]["esik_asildi"] is True
    assert result["belirsiz_fiziksel_tip"] is True


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_failure_type_probability_is_controlled(probability):
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model(
        {"TWF": probability, "HDF": 0.1, "PWF": 0.1, "OSF": 0.1}
    )
    with pytest.raises(ModelHizmetiHatasi):
        hiyerarsik_risk_tahmini_yap(
            sensor(), binary_model=binary, failure_type_model=failure
        )


@pytest.mark.parametrize("classes", [(0, 2), (False, True), (0, 1, 1)])
def test_invalid_failure_type_positive_class_is_controlled(classes):
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model()
    failure.pipelines["TWF"] = FakePipeline(0.8, classes=classes)
    with pytest.raises(ModelHizmetiHatasi):
        hiyerarsik_risk_tahmini_yap(
            sensor(), binary_model=binary, failure_type_model=failure
        )


def test_invalid_failure_type_probability_shape_is_controlled():
    binary = YukluModel(FakePipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_type_model()
    failure.pipelines["TWF"] = BadShapePipeline(0.8)
    with pytest.raises(ModelHizmetiHatasi):
        hiyerarsik_risk_tahmini_yap(
            sensor(), binary_model=binary, failure_type_model=failure
        )


def test_failure_type_cache_reuses_and_path_change_reloads(monkeypatch):
    binary_calls = []
    failure_calls = []

    def binary_loader(*paths):
        binary_calls.append(paths)
        return YukluModel(FakePipeline(), 0.6, MODEL_VERSION, PIPELINE_VERSION)

    def failure_loader(*paths):
        failure_calls.append(paths)
        return failure_type_model()

    monkeypatch.setattr("apps.tahminler.services._model_yukle", binary_loader)
    monkeypatch.setattr(
        "apps.tahminler.services._ariza_tipi_model_yukle", failure_loader
    )
    binary = modeli_getir(artifact_path="binary-a", metadata_path="binary-m")
    first = ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    second = ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    changed = ariza_tipi_modeli_getir(artifact_path="b", metadata_path="m")
    assert first is second
    assert changed is not first
    assert modeli_getir(artifact_path="binary-a", metadata_path="binary-m") is binary
    assert binary_calls == [("binary-a", "binary-m")]
    assert failure_calls == [("a", "m"), ("b", "m")]


def test_model_caches_reset_independently(monkeypatch):
    binary_calls = 0
    failure_calls = 0

    def binary_loader(*paths):
        nonlocal binary_calls
        binary_calls += 1
        return YukluModel(FakePipeline(), 0.6, MODEL_VERSION, PIPELINE_VERSION)

    def failure_loader(*paths):
        nonlocal failure_calls
        failure_calls += 1
        return failure_type_model()

    monkeypatch.setattr("apps.tahminler.services._model_yukle", binary_loader)
    monkeypatch.setattr(
        "apps.tahminler.services._ariza_tipi_model_yukle", failure_loader
    )
    binary = modeli_getir(artifact_path="binary", metadata_path="binary-metadata")
    failure = ariza_tipi_modeli_getir(
        artifact_path="failure", metadata_path="failure-metadata"
    )

    ariza_tipi_model_cache_sifirla()
    assert (
        modeli_getir(artifact_path="binary", metadata_path="binary-metadata") is binary
    )
    assert (
        ariza_tipi_modeli_getir(
            artifact_path="failure", metadata_path="failure-metadata"
        )
        is not failure
    )
    assert (binary_calls, failure_calls) == (1, 2)

    current_failure = ariza_tipi_modeli_getir(
        artifact_path="failure", metadata_path="failure-metadata"
    )
    binary_model_cache_sifirla()
    assert (
        modeli_getir(artifact_path="binary", metadata_path="binary-metadata")
        is not binary
    )
    assert (
        ariza_tipi_modeli_getir(
            artifact_path="failure", metadata_path="failure-metadata"
        )
        is current_failure
    )
    assert (binary_calls, failure_calls) == (2, 2)


def test_binary_path_change_does_not_reload_failure_type(monkeypatch):
    binary_calls = []
    failure_calls = []

    def binary_loader(*paths):
        binary_calls.append(paths)
        return YukluModel(FakePipeline(), 0.6, MODEL_VERSION, PIPELINE_VERSION)

    def failure_loader(*paths):
        failure_calls.append(paths)
        return failure_type_model()

    monkeypatch.setattr("apps.tahminler.services._model_yukle", binary_loader)
    monkeypatch.setattr(
        "apps.tahminler.services._ariza_tipi_model_yukle", failure_loader
    )
    first_binary = modeli_getir(artifact_path="binary-a", metadata_path="metadata")
    failure = ariza_tipi_modeli_getir(
        artifact_path="failure", metadata_path="failure-metadata"
    )
    changed_binary = modeli_getir(artifact_path="binary-b", metadata_path="metadata")

    assert changed_binary is not first_binary
    assert (
        ariza_tipi_modeli_getir(
            artifact_path="failure", metadata_path="failure-metadata"
        )
        is failure
    )
    assert binary_calls == [("binary-a", "metadata"), ("binary-b", "metadata")]
    assert failure_calls == [("failure", "failure-metadata")]


def test_failure_type_failed_load_is_not_cached(monkeypatch):
    calls = 0

    def loader(*paths):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ModelHizmetiHatasi()
        return failure_type_model()

    monkeypatch.setattr("apps.tahminler.services._ariza_tipi_model_yukle", loader)
    with pytest.raises(ModelHizmetiHatasi):
        ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    assert ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    assert calls == 2


def test_failure_type_cache_reset_forces_reload(monkeypatch):
    calls = 0

    def loader(*paths):
        nonlocal calls
        calls += 1
        return failure_type_model()

    monkeypatch.setattr("apps.tahminler.services._ariza_tipi_model_yukle", loader)
    first = ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    ariza_tipi_model_cache_sifirla()
    second = ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m")
    assert first is not second
    assert calls == 2


def test_concurrent_first_failure_type_load_happens_once(monkeypatch):
    calls = 0
    start = threading.Barrier(3)
    entered = threading.Event()
    release = threading.Event()
    results = []

    def loader(*paths):
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(timeout=2)
        return failure_type_model()

    def worker():
        start.wait()
        results.append(ariza_tipi_modeli_getir(artifact_path="a", metadata_path="m"))

    monkeypatch.setattr("apps.tahminler.services._ariza_tipi_model_yukle", loader)
    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    start.wait()
    assert entered.wait(timeout=2)
    release.set()
    for thread in threads:
        thread.join(timeout=2)
    assert not any(thread.is_alive() for thread in threads)
    assert calls == 1
    assert results[0] is results[1]
