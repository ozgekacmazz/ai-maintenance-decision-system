from copy import deepcopy

from sklearn.metrics import average_precision_score

REPLAY_POLICY_VERSION = "sensor-replay-1.0.0"
DEFAULT_BATCH_SIZE = 5
MAX_BATCH_SIZE = 25
DEFAULT_SESSION_LIMIT = 250
MAX_SESSION_LIMIT = 1000
MAX_ATTEMPTS = 3
CLAIM_TIMEOUT_SECONDS = 600
SENSOR_FIELDS = (
    "urun_tipi",
    "hava_sicakligi_k",
    "proses_sicakligi_k",
    "donus_hizi_rpm",
    "tork_nm",
    "takim_asinmasi_dk",
)
GROUND_TRUTH_FIELDS = ("makine_arizasi", "TWF", "HDF", "PWF", "OSF", "RNF")
TRANSITIONS = {
    "HAZIR": frozenset({"CALISIYOR", "IPTAL_EDILDI"}),
    "CALISIYOR": frozenset({"DURAKLATILDI", "TAMAMLANDI", "HATALI", "IPTAL_EDILDI"}),
    "DURAKLATILDI": frozenset({"CALISIYOR", "IPTAL_EDILDI"}),
    "HATALI": frozenset({"CALISIYOR", "IPTAL_EDILDI"}),
    "TAMAMLANDI": frozenset(),
    "IPTAL_EDILDI": frozenset(),
}


class ReplayPolitikaHatasi(ValueError):
    pass


def gecisi_dogrula(current, target):
    if target == current or target not in TRANSITIONS.get(current, ()):
        raise ReplayPolitikaHatasi("Replay durum geçişi geçersizdir.")


def snapshots_from_row(row):
    source = deepcopy(dict(row))
    return (
        {key: source[key] for key in SENSOR_FIELDS},
        {key: int(source[key]) for key in GROUND_TRUTH_FIELDS},
    )


def _label_metrics(truth, predicted):
    tp = sum(a and b for a, b in zip(truth, predicted, strict=True))
    fp = sum(not a and b for a, b in zip(truth, predicted, strict=True))
    fn = sum(a and not b for a, b in zip(truth, predicted, strict=True))
    tn = len(truth) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "support": sum(truth),
        "predicted_positive": sum(predicted),
    }


def _unavailable_metrics(warnings):
    return {
        "degerlendirilen_oge_sayisi": 0,
        "binary": None,
        "failure_types": {},
        "rnf_ground_truth_count": 0,
        "metrik_uyarilari": warnings,
    }


def replay_metrics(records, *, tamamlandi=True):
    data = deepcopy(records)
    if not tamamlandi:
        return _unavailable_metrics(
            ["Replay tamamlanmadan nihai model metrikleri hesaplanmaz."]
        )
    if not data:
        return _unavailable_metrics(
            ["Değerlendirilebilir başarılı replay öğesi bulunamadı."]
        )

    truth = [bool(x["truth"]["makine_arizasi"]) for x in data]
    predicted = [
        (
            float(x["risk_orani"]) >= float(x["binary_threshold"])
            if x.get("risk_orani") is not None
            else bool(x.get("risk_uyarisi", False))
        )
        for x in data
    ]
    binary = _label_metrics(
        truth,
        predicted,
    )
    binary["confusion_matrix"] = {
        "true_negative": binary.pop("tn"),
        "false_positive": binary.pop("fp"),
        "false_negative": binary.pop("fn"),
        "true_positive": binary.pop("tp"),
    }
    warnings = []
    scores = [x.get("risk_orani") for x in data]
    if any(score is None or not 0 <= float(score) <= 1 for score in scores):
        binary["pr_auc"] = None
        warnings.append(
            "PR-AUC hesaplanamadı: bütün öğelerde 0–1 aralığında risk skoru gereklidir."
        )
    elif not any(truth):
        binary["pr_auc"] = None
        warnings.append(
            "PR-AUC hesaplanamadı: replay içinde gerçek pozitif arıza örneği yok."
        )
    else:
        binary["pr_auc"] = round(
            float(average_precision_score(truth, [float(x) for x in scores])), 6
        )
    labels = {}
    for label in ("HDF", "PWF", "OSF", "TWF"):
        labels[label] = _label_metrics(
            [bool(x["truth"][label]) for x in data],
            [label in x["predicted_labels"] for x in data],
        )
        labels[label]["politika"] = "DENEYSEL" if label == "TWF" else "GUVENILIR_ADAY"
    return {
        "degerlendirilen_oge_sayisi": len(data),
        "binary": binary,
        "failure_types": labels,
        "rnf_ground_truth_count": sum(bool(x["truth"]["RNF"]) for x in data),
        "metrik_uyarilari": warnings,
    }
