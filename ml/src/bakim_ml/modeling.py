from dataclasses import asdict, dataclass

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data_contract import MODEL_FEATURE_COLUMNS

RANDOM_SEED = 42
CATEGORICAL_FEATURES = ("urun_tipi",)
NUMERIC_FEATURES = tuple(
    column for column in MODEL_FEATURE_COLUMNS if column not in CATEGORICAL_FEATURES
)


@dataclass(frozen=True)
class Metrics:
    precision: float
    recall: float
    f1: float
    pr_auc: float
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int

    def to_dict(self):
        return asdict(self)


def build_preprocessor():
    return ColumnTransformer(
        transformers=(
            ("numeric", StandardScaler(), list(NUMERIC_FEATURES)),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_FEATURES),
            ),
        ),
        remainder="drop",
        verbose_feature_names_out=False,
    )


def candidate_models():
    return {
        "logistic_regression_none": LogisticRegression(
            class_weight=None, max_iter=2000, random_state=RANDOM_SEED
        ),
        "logistic_regression_balanced": LogisticRegression(
            class_weight="balanced", max_iter=2000, random_state=RANDOM_SEED
        ),
        "random_forest_none": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight=None,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
        "random_forest_balanced": RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_SEED,
            n_jobs=-1,
        ),
    }


def select_candidate_by_pr_auc(evaluations):
    return max(evaluations, key=lambda name: evaluations[name]["validation_pr_auc"])


def build_pipeline(estimator):
    return Pipeline((("preprocessor", build_preprocessor()), ("model", estimator)))


def threshold_candidates(probabilities):
    return np.unique(np.concatenate(([0.0], probabilities, [1.0])))


def select_threshold(y_true, probabilities, *, tolerance=1e-12):
    """Validation F1'i maksimize eder; yakın eşitlikte recall'u tercih eder."""
    best = None
    for threshold in threshold_candidates(probabilities):
        metrics = evaluate(y_true, probabilities, threshold)
        candidate = (metrics.f1, metrics.recall, -float(threshold), float(threshold))
        if best is None or candidate[0] > best[0] + tolerance:
            best = candidate
        elif abs(candidate[0] - best[0]) <= tolerance and candidate[1:] > best[1:]:
            best = candidate
    return best[3]


def select_recall_focused_threshold(y_true, probabilities, *, target_recall=0.90):
    eligible = []
    all_candidates = []
    for threshold in threshold_candidates(probabilities):
        metrics = evaluate(y_true, probabilities, threshold)
        candidate = (metrics.precision, metrics.f1, -threshold, threshold)
        all_candidates.append((metrics.recall, *candidate))
        if metrics.recall >= target_recall:
            eligible.append(candidate)
    return float(max(eligible)[-1] if eligible else max(all_candidates)[-1])


def select_hypothetical_cost_threshold(
    y_true, probabilities, *, false_negative_cost=5, false_positive_cost=1
):
    thresholds = np.unique(np.concatenate(([0.0], probabilities, [1.0])))
    candidates = []
    for threshold in thresholds:
        predictions = (probabilities >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=(0, 1)).ravel()
        cost = false_negative_cost * fn + false_positive_cost * fp
        candidates.append(
            (cost, -recall_score(y_true, predictions, zero_division=0), threshold)
        )
    _, _, threshold = min(candidates)
    return float(threshold)


def threshold_comparison(y_true, probabilities):
    thresholds = {
        "fixed_0_50": 0.50,
        "fixed_0_60": 0.60,
        "max_validation_f1": select_threshold(y_true, probabilities),
        "recall_focused": select_recall_focused_threshold(y_true, probabilities),
        "hypothetical_cost_5_to_1": select_hypothetical_cost_threshold(
            y_true, probabilities
        ),
    }
    return {
        name: {
            "threshold": float(threshold),
            **evaluate(y_true, probabilities, threshold).to_dict(),
            "predicted_positive_count": int((probabilities >= threshold).sum()),
        }
        for name, threshold in thresholds.items()
    }


def evaluate(y_true, probabilities, threshold):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=(0, 1)).ravel()
    return Metrics(
        precision=float(precision_score(y_true, predictions, zero_division=0)),
        recall=float(recall_score(y_true, predictions, zero_division=0)),
        f1=float(f1_score(y_true, predictions, zero_division=0)),
        pr_auc=float(average_precision_score(y_true, probabilities)),
        true_negative=int(tn),
        false_positive=int(fp),
        false_negative=int(fn),
        true_positive=int(tp),
    )


def feature_frame(frame):
    forbidden = {
        "makine_arizasi",
        "TWF",
        "HDF",
        "PWF",
        "OSF",
        "RNF",
        "udi",
        "urun_kodu",
    }
    assert not forbidden & set(MODEL_FEATURE_COLUMNS)
    return frame.loc[:, MODEL_FEATURE_COLUMNS].copy()
