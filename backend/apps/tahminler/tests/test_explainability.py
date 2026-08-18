import threading

import numpy as np
import pandas as pd
import pytest
from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS, PIPELINE_VERSION
from bakim_ml.explainability import ExplainabilityError

from apps.tahminler import explainability, services
from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.services import (
    FAILURE_TYPE_MODEL_VERSION,
    MODEL_VERSION,
    YukluArizaTipiModeli,
    YukluModel,
)
from config.settings.base import env_int


class Pipeline:
    classes_ = np.asarray((0, 1))

    def __init__(self, probability):
        self.probability = probability

    def predict_proba(self, features):
        return np.asarray([[1 - self.probability, self.probability]])


def sensor():
    return {
        "urun_tipi": "L",
        "hava_sicakligi_k": 298.1,
        "proses_sicakligi_k": 308.6,
        "donus_hizi_rpm": 1551.0,
        "tork_nm": 42.8,
        "takim_asinmasi_dk": 0.0,
    }


def failure_model(probabilities):
    return YukluArizaTipiModeli(
        {label: Pipeline(value) for label, value in probabilities.items()},
        {"TWF": 0.2, "HDF": 0.2, "PWF": 0.2, "OSF": 0.2},
        FAILURE_TYPE_MODEL_VERSION,
        PIPELINE_VERSION,
    )


@pytest.fixture(autouse=True)
def clean_caches():
    explainability.explainer_cache_sifirla()
    yield
    explainability.explainer_cache_sifirla()


def test_low_risk_never_calls_explanation_or_failure_model(monkeypatch):
    binary = YukluModel(Pipeline(0.1), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    monkeypatch.setattr(
        services,
        "aciklama_uret",
        lambda *args, **kwargs: pytest.fail("SHAP çağrılmamalı"),
    )
    monkeypatch.setattr(
        services,
        "ariza_tipi_modeli_getir",
        lambda: pytest.fail("Failure-type yüklenmemeli"),
    )
    result = services.hiyerarsik_risk_tahmini_yap(sensor(), binary_model=binary)
    assert result["aciklanabilirlik"] == {
        "durum": "RISK_ESIK_ALTINDA",
        "risk_aciklamasi": None,
    }


def test_high_risk_explains_only_binary_threshold_candidates_and_twf(monkeypatch):
    calls = []

    def fake_explanation(pipeline, features, *, target, probability, **kwargs):
        calls.append((pipeline, target, probability, features.copy(deep=True)))
        return {
            "target": target,
            "output_space": "probability",
            "base_value": 0.0,
            "ilk_etkiler": [{"feature": "tork_nm"}] * 3,
        }

    monkeypatch.setattr(services, "aciklama_uret", fake_explanation)
    binary = YukluModel(Pipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_model({"TWF": 0.8, "HDF": 0.9, "PWF": 0.1, "OSF": 0.1})
    result = services.hiyerarsik_risk_tahmini_yap(
        sensor(), binary_model=binary, failure_type_model=failure
    )

    assert [target for _, target, _, _ in calls] == ["machine_failure", "HDF", "TWF"]
    assert calls[0][0] is binary.pipeline
    assert calls[1][0] is failure.pipelines["HDF"]
    assert result["aciklanabilirlik"]["durum"] == "ACIKLANDI"
    assert (
        result["ariza_tipi_degerlendirmesi"]["deneysel_sinyaller"][0][
            "operasyonel_kullanima_uygun"
        ]
        is False
    )
    assert "RNF" not in str(result)


def test_twf_below_threshold_is_not_explained(monkeypatch):
    targets = []

    def fake_explanation(pipeline, features, *, target, **kwargs):
        targets.append(target)
        return {
            "target": target,
            "output_space": "probability",
            "base_value": 0.0,
            "ilk_etkiler": [],
        }

    monkeypatch.setattr(services, "aciklama_uret", fake_explanation)
    binary = YukluModel(Pipeline(0.9), 0.6, MODEL_VERSION, PIPELINE_VERSION)
    failure = failure_model({"TWF": 0.1, "HDF": 0.1, "PWF": 0.1, "OSF": 0.1})
    result = services.hiyerarsik_risk_tahmini_yap(
        sensor(), binary_model=binary, failure_type_model=failure
    )
    assert targets == ["machine_failure"]
    assert (
        "aciklama" not in result["ariza_tipi_degerlendirmesi"]["deneysel_sinyaller"][0]
    )


def test_explainer_caches_are_model_bound_and_independent(monkeypatch):
    created = []
    monkeypatch.setattr(
        explainability,
        "create_tree_explainer",
        lambda pipeline: created.append(pipeline) or object(),
    )
    binary_a, binary_b = Pipeline(0.8), Pipeline(0.9)
    failure_a, failure_b = Pipeline(0.7), Pipeline(0.6)

    first_binary = explainability.binary_explainer_getir(binary_a)
    assert explainability.binary_explainer_getir(binary_a) is first_binary
    first_failure = explainability.ariza_tipi_explainer_getir("HDF", failure_a)
    assert explainability.ariza_tipi_explainer_getir("HDF", failure_a) is first_failure
    assert explainability.binary_explainer_getir(binary_b) is not first_binary
    assert (
        explainability.ariza_tipi_explainer_getir("HDF", failure_b) is not first_failure
    )
    assert created == [binary_a, failure_a, binary_b, failure_b]

    explainability.binary_explainer_cache_sifirla()
    assert explainability.ariza_tipi_explainer_getir("HDF", failure_b) is not None
    assert len(created) == 4
    explainability.ariza_tipi_explainer_cache_sifirla("HDF")
    explainability.ariza_tipi_explainer_getir("HDF", failure_b)
    assert len(created) == 5


def test_failed_explainer_creation_is_not_cached(monkeypatch):
    calls = 0

    def create(pipeline):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ExplainabilityError("safe")
        return object()

    monkeypatch.setattr(explainability, "create_tree_explainer", create)
    pipeline = Pipeline(0.8)
    with pytest.raises(ExplainabilityError):
        explainability.binary_explainer_getir(pipeline)
    assert explainability.binary_explainer_getir(pipeline) is not None
    assert calls == 2


def test_concurrent_first_binary_explainer_creation_happens_once(monkeypatch):
    calls = 0
    start = threading.Barrier(3)
    entered = threading.Event()
    release = threading.Event()
    results = []

    def create(pipeline):
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(timeout=2)
        return object()

    def worker():
        start.wait()
        results.append(explainability.binary_explainer_getir(pipeline))

    monkeypatch.setattr(explainability, "create_tree_explainer", create)
    pipeline = Pipeline(0.8)
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


def test_all_transformed_features_have_safe_original_and_model_values():
    prepared = services._ozellikleri_hazirla(sensor())
    contributions = [
        {
            "feature": feature,
            "feature_value": float(index),
            "shap_value": 0.01,
            "direction": "RISKI_ARTIRIR",
        }
        for index, feature in enumerate(explainability.FEATURE_PRESENTATION)
    ]
    result = explainability._sunuma_cevir(
        {
            "target": "machine_failure",
            "output_space": "probability",
            "base_value": 0.1,
            "feature_contributions": contributions,
        },
        prepared,
    )
    effects = {item["feature"]: item for item in result["ilk_etkiler"]}
    assert set(effects) == set(explainability.FEATURE_PRESENTATION)
    assert effects["tork_nm"]["original_feature_value"] == 42.8
    assert effects["proses_hava_sicaklik_farki_k"]["original_feature_value"] == 10.5
    assert effects["urun_tipi_L"]["original_feature_value"] is True
    assert effects["urun_tipi_H"]["original_feature_value"] is False
    assert effects["tork_nm"]["model_feature_value"] != 42.8
    assert effects["tork_nm"]["birim"] == "Nm"


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_presentation_rejects_non_finite_values(bad):
    prepared = pd.DataFrame([sensor()]).reindex(columns=MODEL_FEATURE_COLUMNS)
    with pytest.raises(ExplainabilityError):
        explainability._sunuma_cevir(
            {
                "target": "x",
                "output_space": "probability",
                "base_value": 0.0,
                "feature_contributions": [
                    {
                        "feature": "tork_nm",
                        "feature_value": bad,
                        "shap_value": 0.1,
                        "direction": "NOTR",
                    }
                ],
            },
            prepared,
        )


def test_unknown_feature_becomes_controlled_model_service_error(monkeypatch):
    monkeypatch.setattr(
        explainability, "binary_explainer_getir", lambda pipeline: object()
    )
    monkeypatch.setattr(
        explainability,
        "explain_prepared_pipeline",
        lambda *args, **kwargs: {
            "target": "machine_failure",
            "output_space": "probability",
            "base_value": 0.0,
            "feature_contributions": [
                {
                    "feature": "unknown",
                    "feature_value": 1.0,
                    "shap_value": 0.1,
                    "direction": "RISKI_ARTIRIR",
                }
            ],
        },
    )
    with pytest.raises(ModelHizmetiHatasi):
        explainability.aciklama_uret(
            Pipeline(0.8),
            services._ozellikleri_hazirla(sensor()),
            target="machine_failure",
            probability=0.8,
            top_n=3,
        )


@pytest.mark.parametrize("value", ["true", "0", "6", "3.0"])
def test_shap_top_n_configuration_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("TEST_SHAP_TOP_N", value)
    with pytest.raises(RuntimeError):
        env_int("TEST_SHAP_TOP_N", 3, minimum=1, maximum=5)


def test_shap_top_n_configuration_accepts_one_through_five(monkeypatch):
    for value in range(1, 6):
        monkeypatch.setenv("TEST_SHAP_TOP_N", str(value))
        assert env_int("TEST_SHAP_TOP_N", 3, minimum=1, maximum=5) == value
