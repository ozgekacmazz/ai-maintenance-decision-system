import json
from datetime import UTC, datetime
from hashlib import sha256
from itertools import combinations
from pathlib import Path

from .data_contract import FAILURE_TYPE_COLUMNS, MODEL_FEATURE_COLUMNS
from .training import RANDOM_SEED, split_dataset

ANALYSIS_VERSION = "1.0.0"
NONE_LABEL = "NONE"
DEFAULT_METADATA = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "metadata"
    / "failure_label_analysis.json"
)


class FailureLabelAnalysisError(Exception):
    pass


def _validate_frame(frame):
    if frame.empty:
        raise FailureLabelAnalysisError("Analiz verisi boş olamaz.")
    required = {"makine_arizasi", *FAILURE_TYPE_COLUMNS}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise FailureLabelAnalysisError(
            f"Zorunlu hedef sütunları eksik: {', '.join(missing)}"
        )
    for column in required:
        if frame[column].isna().any() or not frame[column].isin((0, 1)).all():
            raise FailureLabelAnalysisError(
                f"{column} yalnız 0/1 değerleri içermelidir."
            )


def _combination_name(row):
    labels = [label for label in FAILURE_TYPE_COLUMNS if int(row[label]) == 1]
    return "+".join(labels) if labels else NONE_LABEL


def _consistency(frame, label_sum):
    machine = frame["makine_arizasi"]
    return {
        "machine_failure_0_no_type": int(((machine == 0) & (label_sum == 0)).sum()),
        "machine_failure_1_with_type": int(((machine == 1) & (label_sum >= 1)).sum()),
        "machine_failure_1_no_type": int(((machine == 1) & (label_sum == 0)).sum()),
        "machine_failure_0_with_type": int(((machine == 0) & (label_sum >= 1)).sum()),
        "multiple_types_machine_failure_1": int(
            ((machine == 1) & (label_sum > 1)).sum()
        ),
        "multiple_types_machine_failure_0": int(
            ((machine == 0) & (label_sum > 1)).sum()
        ),
    }


def _split_statistics(frame):
    parts = split_dataset(frame)
    result = {}
    all_indexes = []
    for name, part in zip(("train", "validation", "test"), parts, strict=True):
        label_sum = part[list(FAILURE_TYPE_COLUMNS)].sum(axis=1)
        result[name] = {
            "rows": int(len(part)),
            "machine_failure_positive": int(part["makine_arizasi"].sum()),
            "label_positive_counts": {
                label: int(part[label].sum()) for label in FAILURE_TYPE_COLUMNS
            },
            "multiple_label_rows": int((label_sum > 1).sum()),
            "rnf_positive": int(part["RNF"].sum()),
            "machine_failure_1_no_type": int(
                ((part["makine_arizasi"] == 1) & (label_sum == 0)).sum()
            ),
            "machine_failure_0_with_type": int(
                ((part["makine_arizasi"] == 0) & (label_sum >= 1)).sum()
            ),
        }
        all_indexes.extend(part.index.tolist())
    result["contract"] = {
        "random_seed": RANDOM_SEED,
        "strategy": "binary_machine_failure_stratified_70_15_15",
        "all_rows_once": len(all_indexes) == len(frame)
        and len(set(all_indexes)) == len(frame),
    }
    return result


def analyze_failure_labels(frame):
    _validate_frame(frame)
    labels = list(FAILURE_TYPE_COLUMNS)
    label_frame = frame[labels]
    label_sum = label_frame.sum(axis=1)
    combination_counts = frame.apply(_combination_name, axis=1).value_counts()
    combination_order = [NONE_LABEL]
    combination_order.extend(
        "+".join(group)
        for size in range(1, len(labels) + 1)
        for group in combinations(labels, size)
    )
    label_counts = {
        label: {
            "positive": int(label_frame[label].sum()),
            "negative": int(len(frame) - label_frame[label].sum()),
        }
        for label in labels
    }
    pairwise = {
        f"{left}+{right}": int(
            ((label_frame[left] == 1) & (label_frame[right] == 1)).sum()
        )
        for left, right in combinations(labels, 2)
    }
    rnf_positive = frame["RNF"] == 1
    return {
        "total_rows": int(len(frame)),
        "machine_failure_counts": {
            "0": int((frame["makine_arizasi"] == 0).sum()),
            "1": int((frame["makine_arizasi"] == 1).sum()),
        },
        "target_columns": labels,
        "label_counts": label_counts,
        "label_prevalence": {
            label: float(label_counts[label]["positive"] / len(frame))
            for label in labels
        },
        "label_cardinality": float(label_sum.mean()),
        "label_density": float(label_sum.mean() / len(labels)),
        "rows_with_no_label": int((label_sum == 0).sum()),
        "rows_with_single_label": int((label_sum == 1).sum()),
        "rows_with_multiple_labels": int((label_sum > 1).sum()),
        "max_labels_per_row": int(label_sum.max()),
        "label_combinations": {
            name: int(combination_counts.get(name, 0))
            for name in combination_order
            if combination_counts.get(name, 0) > 0
        },
        "pairwise_cooccurrence": pairwise,
        "machine_failure_consistency": _consistency(frame, label_sum),
        "rnf_analysis": {
            "positive": int(rnf_positive.sum()),
            "machine_failure_0": int(
                (rnf_positive & (frame["makine_arizasi"] == 0)).sum()
            ),
            "machine_failure_1": int(
                (rnf_positive & (frame["makine_arizasi"] == 1)).sum()
            ),
            "with_other_failure_type": int((rnf_positive & (label_sum > 1)).sum()),
        },
        "split": _split_statistics(frame),
        "recommended_problem_type": "hierarchical_multi_label",
        "recommended_modeled_labels": ["TWF", "HDF", "PWF", "OSF"],
        "excluded_or_policy_labels": {
            "RNF": "model_disinda_raporla_ve_genel_teknik_incelemeye_yonlendir"
        },
        "recommendation_reasons": [
            "Aynı satırda birden fazla fiziksel arıza tipi bulunabilir.",
            (
                "RNF az sayıda, ana hedefle büyük ölçüde tutarsız ve "
                "rastlantısal semantiklidir."
            ),
            (
                "Binary risk ve fiziksel arıza tipi kararları ayrı servis "
                "aşamaları olmalıdır."
            ),
        ],
        "warnings": [
            "Binary stratification, her arıza tipi dağılımını korumaz.",
            (
                "Az destekli etiketlerde validation ve test PR-AUC/recall "
                "yüksek varyanslıdır."
            ),
            "AI4I sentetik bir veri setidir; saha genellemesi kanıtlanmamıştır.",
        ],
        "model_feature_columns": list(MODEL_FEATURE_COLUMNS),
    }


def build_analysis_metadata(
    frame,
    *,
    source_sha256,
    prepared_source_sha256,
    created_at=None,
):
    document = {
        "analysis_version": ANALYSIS_VERSION,
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "source_sha256": source_sha256,
        "prepared_source_sha256": prepared_source_sha256,
        **analyze_failure_labels(frame),
    }
    fingerprint_payload = {k: v for k, v in document.items() if k != "created_at"}
    canonical = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    document["analysis_fingerprint_sha256"] = sha256(canonical.encode()).hexdigest()
    return document


def write_analysis_metadata(document, path=DEFAULT_METADATA):
    serialized = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized + "\n", encoding="utf-8")
