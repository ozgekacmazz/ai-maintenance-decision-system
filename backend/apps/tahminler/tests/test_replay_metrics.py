from copy import deepcopy

import pytest
from sklearn.metrics import average_precision_score

from apps.tahminler.replay_policy import replay_metrics


def record(truth, score, threshold=0.5):
    return {
        "truth": {
            "makine_arizasi": truth,
            "HDF": 0,
            "PWF": 0,
            "OSF": 0,
            "TWF": 0,
            "RNF": 0,
        },
        "risk_orani": score,
        "binary_threshold": threshold,
        "predicted_labels": set(),
    }


def test_balanced_binary_contract_uses_scores_for_pr_auc_and_threshold_for_matrix():
    records = [record(0, 0.1), record(0, 0.7), record(1, 0.4), record(1, 0.9)]
    original = deepcopy(records)

    result = replay_metrics(records)
    binary = result["binary"]

    assert set(result) == {
        "degerlendirilen_oge_sayisi",
        "binary",
        "failure_types",
        "rnf_ground_truth_count",
        "metrik_uyarilari",
    }
    assert "accuracy" not in str(result).lower()
    assert result["degerlendirilen_oge_sayisi"] == 4
    assert binary["confusion_matrix"] == {
        "true_negative": 1,
        "false_positive": 1,
        "false_negative": 1,
        "true_positive": 1,
    }
    assert binary["precision"] == binary["recall"] == binary["f1"] == 0.5
    assert binary["pr_auc"] == round(
        average_precision_score([0, 0, 1, 1], [0.1, 0.7, 0.4, 0.9]), 6
    )
    assert sum(binary["confusion_matrix"].values()) == 4
    assert records == original


@pytest.mark.parametrize(
    ("scores", "expected"),
    [([0.1, 0.2], (2, 0, 0, 0)), ([0.8, 0.9], (0, 2, 0, 0))],
)
def test_only_negative_replay_has_stable_matrix_and_unavailable_pr_auc(
    scores, expected
):
    result = replay_metrics([record(0, score) for score in scores])
    matrix = result["binary"]["confusion_matrix"]
    assert tuple(matrix.values()) == expected
    assert result["binary"]["pr_auc"] is None
    assert result["metrik_uyarilari"]


def test_only_positive_no_positive_predictions_and_all_positive_predictions_are_safe():
    none_positive = replay_metrics([record(1, 0.1), record(1, 0.2)])
    assert none_positive["binary"]["precision"] == 0.0
    assert none_positive["binary"]["recall"] == 0.0
    assert none_positive["binary"]["pr_auc"] == 1.0

    all_positive = replay_metrics([record(0, 0.8), record(1, 0.9)])
    assert all_positive["binary"]["precision"] == 0.5
    assert all_positive["binary"]["recall"] == 1.0


def test_empty_incomplete_and_missing_score_are_valid_unavailable_results():
    empty = replay_metrics([])
    incomplete = replay_metrics([record(1, 0.9)], tamamlandi=False)
    missing_score = replay_metrics([record(1, None)])

    assert empty["binary"] is None and empty["metrik_uyarilari"]
    assert incomplete["binary"] is None and incomplete["metrik_uyarilari"]
    assert missing_score["binary"]["pr_auc"] is None
    assert missing_score["metrik_uyarilari"]
