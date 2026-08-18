from time import perf_counter

import numpy as np
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    hamming_loss,
    precision_score,
    recall_score,
)

from .data_contract import MODELED_FAILURE_TYPE_COLUMNS
from .modeling import (
    build_pipeline,
    candidate_models,
    evaluate,
    feature_frame,
    select_recall_focused_threshold,
    select_threshold,
)


def failure_type_candidates():
    return candidate_models()


class FailureTypeModelingError(Exception):
    pass


def _positive_class_index(pipeline):
    classes = getattr(pipeline, "classes_", ())
    matches = [
        index
        for index, value in enumerate(classes)
        if not isinstance(value, (bool, np.bool_)) and value == 1
    ]
    if len(matches) != 1:
        raise FailureTypeModelingError(
            "Pozitif sınıf 1, pipeline classes_ içinde tam bir kez bulunmalıdır."
        )
    return matches[0]


def _positive_probabilities(pipeline, features):
    return pipeline.predict_proba(features)[:, _positive_class_index(pipeline)]


def fit_candidate(estimator, train, validation):
    pipelines = {}
    label_metrics = {}
    probabilities = []
    fit_started = perf_counter()
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        pipeline = build_pipeline(clone(estimator))
        pipeline.fit(feature_frame(train), train[label])
        pipelines[label] = pipeline
    fit_seconds = perf_counter() - fit_started
    inference_started = perf_counter()
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        probability = _positive_probabilities(
            pipelines[label], feature_frame(validation)
        )
        probabilities.append(probability)
        metrics = evaluate(validation[label], probability, 0.50)
        label_metrics[label] = {
            "support": int(validation[label].sum()),
            **metrics.to_dict(),
            "predicted_positive_count": int((probability >= 0.50).sum()),
        }
    inference_seconds = perf_counter() - inference_started
    probability_matrix = np.column_stack(probabilities)
    target = validation[list(MODELED_FAILURE_TYPE_COLUMNS)].to_numpy(dtype=int)
    predictions = (probability_matrix >= 0.50).astype(int)
    return pipelines, {
        "label_metrics_at_0_50": label_metrics,
        "validation_macro_pr_auc": float(
            np.mean([metrics["pr_auc"] for metrics in label_metrics.values()])
        ),
        "validation_macro_recall_at_0_50": float(
            recall_score(target, predictions, average="macro", zero_division=0)
        ),
        "validation_micro_f1_at_0_50": float(
            f1_score(target, predictions, average="micro", zero_division=0)
        ),
        "validation_macro_f1_at_0_50": float(
            f1_score(target, predictions, average="macro", zero_division=0)
        ),
        "validation_weighted_f1_at_0_50": float(
            f1_score(target, predictions, average="weighted", zero_division=0)
        ),
        "fit_seconds": float(fit_seconds),
        "validation_inference_seconds": float(inference_seconds),
    }


def select_global_candidate(evaluations, *, tolerance=1e-12):
    simplicity = {"LogisticRegression": 1, "RandomForestClassifier": 0}
    best_name = None
    best = None
    for name, result in evaluations.items():
        score = result["validation_macro_pr_auc"]
        recall = result["validation_macro_recall_at_0_50"]
        candidate = (
            score,
            recall,
            simplicity[result["model_family"]],
            int(result["class_weight"] is None),
        )
        if best is None or candidate[0] > best[0] + tolerance:
            best_name, best = name, candidate
        elif abs(candidate[0] - best[0]) <= tolerance and candidate[1:] > best[1:]:
            best_name, best = name, candidate
    return best_name


def select_label_thresholds(validation, probability_by_label):
    thresholds = {}
    comparisons = {}
    for label in MODELED_FAILURE_TYPE_COLUMNS:
        target = validation[label].to_numpy(dtype=int)
        probability = probability_by_label[label]
        selected = float(select_threshold(target, probability))
        recall_focused = float(select_recall_focused_threshold(target, probability))
        thresholds[label] = selected
        comparisons[label] = {
            "fixed_0_50": {
                "threshold": 0.50,
                **evaluate(target, probability, 0.50).to_dict(),
                "predicted_positive_count": int((probability >= 0.50).sum()),
            },
            "max_validation_f1": {
                "threshold": selected,
                **evaluate(target, probability, selected).to_dict(),
                "predicted_positive_count": int((probability >= selected).sum()),
            },
            "recall_focused": {
                "threshold": recall_focused,
                **evaluate(target, probability, recall_focused).to_dict(),
                "predicted_positive_count": int((probability >= recall_focused).sum()),
            },
        }
    return thresholds, comparisons


def evaluate_failure_types(frame, probability_by_label, thresholds):
    targets = frame[list(MODELED_FAILURE_TYPE_COLUMNS)].to_numpy(dtype=int)
    probabilities = np.column_stack(
        [probability_by_label[label] for label in MODELED_FAILURE_TYPE_COLUMNS]
    )
    predictions = np.column_stack(
        [
            probability_by_label[label] >= thresholds[label]
            for label in MODELED_FAILURE_TYPE_COLUMNS
        ]
    ).astype(int)
    per_label = {}
    for index, label in enumerate(MODELED_FAILURE_TYPE_COLUMNS):
        metrics = evaluate(
            targets[:, index], probabilities[:, index], thresholds[label]
        )
        metric_values = metrics.to_dict()
        metric_values["pr_auc"] = min(1.0, max(0.0, metric_values["pr_auc"]))
        per_label[label] = {
            "support": int(targets[:, index].sum()),
            "threshold": float(thresholds[label]),
            **metric_values,
            "predicted_positive_count": int(predictions[:, index].sum()),
        }
    predicted_cardinality = predictions.sum(axis=1)
    aggregate = {
        "micro_precision": float(
            precision_score(targets, predictions, average="micro", zero_division=0)
        ),
        "micro_recall": float(
            recall_score(targets, predictions, average="micro", zero_division=0)
        ),
        "micro_f1": float(
            f1_score(targets, predictions, average="micro", zero_division=0)
        ),
        "macro_precision": float(
            precision_score(targets, predictions, average="macro", zero_division=0)
        ),
        "macro_recall": float(
            recall_score(targets, predictions, average="macro", zero_division=0)
        ),
        "macro_f1": float(
            f1_score(targets, predictions, average="macro", zero_division=0)
        ),
        "weighted_f1": float(
            f1_score(targets, predictions, average="weighted", zero_division=0)
        ),
        "hamming_loss": float(hamming_loss(targets, predictions)),
        "subset_accuracy": float(accuracy_score(targets, predictions)),
        "average_predicted_label_count": float(predicted_cardinality.mean()),
        "rows_with_no_predicted_label": int((predicted_cardinality == 0).sum()),
        "rows_with_any_predicted_label": int((predicted_cardinality >= 1).sum()),
        "rows_with_multiple_predicted_labels": int((predicted_cardinality > 1).sum()),
    }
    return {"per_label": per_label, "aggregate": aggregate}


def predict_probabilities(pipelines, frame):
    features = feature_frame(frame)
    return {
        label: _positive_probabilities(pipelines[label], features)
        for label in MODELED_FAILURE_TYPE_COLUMNS
    }
