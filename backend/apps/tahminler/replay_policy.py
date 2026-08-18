from copy import deepcopy

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


def replay_metrics(records):
    data = deepcopy(records)
    if not data:
        return {
            "evaluated_count": 0,
            "binary": None,
            "failure_types": {},
            "rnf_ground_truth_count": 0,
        }
    binary = _label_metrics(
        [bool(x["truth"]["makine_arizasi"]) for x in data],
        [bool(x["risk_uyarisi"]) for x in data],
    )
    binary["accuracy"] = round((binary["tp"] + binary["tn"]) / len(data), 6)
    labels = {}
    for label in ("HDF", "PWF", "OSF", "TWF"):
        labels[label] = _label_metrics(
            [bool(x["truth"][label]) for x in data],
            [label in x["predicted_labels"] for x in data],
        )
        labels[label]["politika"] = "DENEYSEL" if label == "TWF" else "GUVENILIR_ADAY"
    return {
        "evaluated_count": len(data),
        "binary": binary,
        "failure_types": labels,
        "rnf_ground_truth_count": sum(bool(x["truth"]["RNF"]) for x in data),
    }
