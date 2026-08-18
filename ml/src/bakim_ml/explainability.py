import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier

from .data_contract import MODEL_FEATURE_COLUMNS, MODELED_FAILURE_TYPE_COLUMNS
from .features import add_engineered_features
from .modeling import feature_frame

DIRECTION_TOLERANCE = 1e-12
ADDITIVITY_ABSOLUTE_TOLERANCE = 1e-6
ADDITIVITY_RELATIVE_TOLERANCE = 1e-6
FAILURE_TYPE_EXPLANATION_POLICY = {
    "TWF": {
        "guven_durumu": "YETERSIZ_DESTEK",
        "operasyonel_kullanima_uygun": False,
    }
}


class ExplainabilityError(Exception):
    """Açıklama üretilemediğinde güvenli ML katmanı hatası."""


@dataclass(frozen=True)
class NormalizedShapValues:
    values: np.ndarray
    base_value: float


def positive_class_index(classes):
    matches = [
        index
        for index, value in enumerate(classes)
        if not isinstance(value, (bool, np.bool_)) and value == 1
    ]
    if len(matches) != 1:
        raise ExplainabilityError("Pozitif sınıf sözleşmesi geçersiz.")
    return matches[0]


def _finite_float(value, message):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ExplainabilityError(message) from exc
    if not math.isfinite(result):
        raise ExplainabilityError(message)
    return result


def _normalize_base_value(base_values, positive_index):
    values = np.asarray(base_values)
    if values.ndim == 0:
        return _finite_float(values.item(), "SHAP base value geçersiz.")
    squeezed = np.squeeze(values)
    if squeezed.ndim == 0:
        return _finite_float(squeezed.item(), "SHAP base value geçersiz.")
    if squeezed.ndim == 1 and positive_index < len(squeezed):
        return _finite_float(squeezed[positive_index], "SHAP base value geçersiz.")
    raise ExplainabilityError("SHAP base value şekli desteklenmiyor.")


def normalize_positive_class_shap_values(
    output, *, positive_index, feature_count, base_values=None
):
    if isinstance(feature_count, bool) or not isinstance(feature_count, int):
        raise ExplainabilityError("Feature sayısı geçersiz.")
    if feature_count < 1:
        raise ExplainabilityError("Feature sayısı geçersiz.")

    if isinstance(output, shap.Explanation):
        values = np.asarray(output.values)
        base_values = output.base_values
    elif isinstance(output, (list, tuple)):
        if positive_index >= len(output):
            raise ExplainabilityError("Pozitif sınıf SHAP çıktısı bulunamadı.")
        values = np.asarray(output[positive_index])
    else:
        values = np.asarray(output)

    if values.ndim == 1:
        vector = values
    elif values.ndim == 2 and values.shape == (1, feature_count):
        vector = values[0]
    elif values.ndim == 2 and values.shape == (feature_count, 2):
        vector = values[:, positive_index]
    elif values.ndim == 3 and values.shape[0] == 1:
        if values.shape[1] == feature_count and positive_index < values.shape[2]:
            vector = values[0, :, positive_index]
        elif values.shape[2] == feature_count and positive_index < values.shape[1]:
            vector = values[0, positive_index, :]
        else:
            raise ExplainabilityError("SHAP çıktı şekli desteklenmiyor.")
    else:
        raise ExplainabilityError("SHAP yalnız tek kayıt için normalize edilebilir.")

    vector = np.asarray(vector, dtype=float)
    if vector.shape != (feature_count,):
        raise ExplainabilityError("SHAP feature sayısı modelle uyuşmuyor.")
    if not np.isfinite(vector).all():
        raise ExplainabilityError("SHAP değerleri sonlu değil.")
    if base_values is None:
        raise ExplainabilityError("SHAP base value bulunamadı.")
    return NormalizedShapValues(
        values=vector,
        base_value=_normalize_base_value(base_values, positive_index),
    )


def _validate_top_n(top_n, feature_count):
    if (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 0
        or top_n > feature_count
    ):
        raise ExplainabilityError("top_n geçersiz.")


def _prepare_single_input(canonical_sensor_input):
    if isinstance(canonical_sensor_input, pd.DataFrame):
        if len(canonical_sensor_input) != 1:
            raise ExplainabilityError("Yalnız tek kayıt açıklanabilir.")
        source = canonical_sensor_input.copy(deep=True)
    else:
        try:
            source = pd.DataFrame([dict(canonical_sensor_input)])
        except (TypeError, ValueError) as exc:
            raise ExplainabilityError("Sensör girdisi geçersiz.") from exc
    try:
        return feature_frame(add_engineered_features(source))
    except Exception as exc:
        raise ExplainabilityError(
            "Sensör girdisi açıklama için hazırlanamadı."
        ) from exc


def _pipeline_parts(pipeline):
    try:
        preprocessor = pipeline.named_steps["preprocessor"]
        estimator = pipeline.named_steps["model"]
    except (AttributeError, KeyError) as exc:
        raise ExplainabilityError("Model pipeline sözleşmesi geçersiz.") from exc
    if not isinstance(estimator, RandomForestClassifier):
        raise ExplainabilityError("Estimator TreeExplainer ile desteklenmiyor.")
    return preprocessor, estimator


def _predict_positive_probability(pipeline, features, positive_index):
    try:
        probabilities = np.asarray(pipeline.predict_proba(features), dtype=float)
    except Exception as exc:
        raise ExplainabilityError("Model olasılığı üretilemedi.") from exc
    if (
        probabilities.ndim != 2
        or probabilities.shape[0] != 1
        or positive_index >= probabilities.shape[1]
    ):
        raise ExplainabilityError("Model olasılık şekli geçersiz.")
    return _finite_float(
        probabilities[0, positive_index], "Model olasılığı sonlu değil."
    )


def _direction(value):
    if value > DIRECTION_TOLERANCE:
        return "RISKI_ARTIRIR"
    if value < -DIRECTION_TOLERANCE:
        return "RISKI_AZALTIR"
    return "NOTR"


def _explain_pipeline(pipeline, canonical_sensor_input, target, *, top_n):
    features = _prepare_single_input(canonical_sensor_input)
    if tuple(features.columns) != MODEL_FEATURE_COLUMNS:
        raise ExplainabilityError("Model feature sözleşmesi geçersiz.")
    preprocessor, estimator = _pipeline_parts(pipeline)
    positive_index = positive_class_index(estimator.classes_)
    probability = _predict_positive_probability(pipeline, features, positive_index)
    try:
        transformed = np.asarray(preprocessor.transform(features), dtype=float)
        feature_names = tuple(
            str(name) for name in preprocessor.get_feature_names_out()
        )
    except Exception as exc:
        raise ExplainabilityError("Model feature dönüşümü başarısız.") from exc
    if transformed.ndim != 2 or transformed.shape[0] != 1:
        raise ExplainabilityError("Dönüştürülmüş feature şekli geçersiz.")
    if transformed.shape[1] != len(feature_names):
        raise ExplainabilityError("Feature isimleri ve değerleri uyuşmuyor.")
    if not np.isfinite(transformed).all():
        raise ExplainabilityError("Feature değerleri sonlu değil.")
    _validate_top_n(top_n, len(feature_names))

    try:
        explanation = shap.TreeExplainer(estimator)(transformed, check_additivity=False)
    except Exception as exc:
        raise ExplainabilityError("SHAP açıklaması üretilemedi.") from exc
    normalized = normalize_positive_class_shap_values(
        explanation,
        positive_index=positive_index,
        feature_count=len(feature_names),
    )
    reconstructed = normalized.base_value + float(normalized.values.sum())
    if not math.isclose(
        reconstructed,
        probability,
        rel_tol=ADDITIVITY_RELATIVE_TOLERANCE,
        abs_tol=ADDITIVITY_ABSOLUTE_TOLERANCE,
    ):
        raise ExplainabilityError("SHAP additivity doğrulaması başarısız.")

    contributions = [
        {
            "feature": name,
            "feature_value": _finite_float(value, "Feature değeri sonlu değil."),
            "shap_value": _finite_float(shap_value, "SHAP değeri sonlu değil."),
            "direction": _direction(float(shap_value)),
        }
        for name, value, shap_value in zip(
            feature_names, transformed[0], normalized.values, strict=True
        )
    ]
    contributions.sort(key=lambda item: (-abs(item["shap_value"]), item["feature"]))
    return {
        "target": target,
        "predicted_probability": probability,
        "base_value": normalized.base_value,
        "output_space": "probability",
        "transformed_feature_space": True,
        "feature_contributions": contributions[:top_n],
    }


def explain_binary_prediction(artifact, canonical_sensor_input, *, top_n=5):
    try:
        pipeline = artifact["pipeline"]
        metadata = artifact["metadata"]
    except (KeyError, TypeError) as exc:
        raise ExplainabilityError("Binary artefakt sözleşmesi geçersiz.") from exc
    if metadata.get("target") != "makine_arizasi":
        raise ExplainabilityError("Binary hedef sözleşmesi geçersiz.")
    return _explain_pipeline(
        pipeline, canonical_sensor_input, "machine_failure", top_n=top_n
    )


def explain_failure_type_prediction(
    artifact, canonical_sensor_input, label, *, top_n=5
):
    if label == "RNF" or label not in MODELED_FAILURE_TYPE_COLUMNS:
        raise ExplainabilityError("Arıza tipi açıklama hedefi geçersiz.")
    try:
        metadata = artifact["metadata"]
        pipelines = artifact["pipelines"]
    except (KeyError, TypeError) as exc:
        raise ExplainabilityError("Arıza tipi artefakt sözleşmesi geçersiz.") from exc
    if tuple(metadata.get("target_labels", ())) != MODELED_FAILURE_TYPE_COLUMNS:
        raise ExplainabilityError("Arıza tipi hedef sözleşmesi geçersiz.")
    result = _explain_pipeline(
        pipelines[label], canonical_sensor_input, label, top_n=top_n
    )
    result.update(FAILURE_TYPE_EXPLANATION_POLICY.get(label, {}))
    return result
