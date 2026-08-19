import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from .data_contract import MODEL_FEATURE_COLUMNS
from .features import add_engineered_features
from .loaders import file_sha256, load_prepared_dataset
from .training import split_dataset


def generate_input_domain_contract(dataset_path, policy_path):
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    prepared_hash = file_sha256(dataset_path)
    frame = load_prepared_dataset(dataset_path, expected_sha256=prepared_hash)
    train, _, _ = split_dataset(add_engineered_features(frame))
    features = deepcopy(policy["features"])
    for name in MODEL_FEATURE_COLUMNS:
        config = features[name]
        if name == "urun_tipi":
            continue
        values = train[name].astype(float)
        config.update(
            observed_min=float(values.min()),
            observed_max=float(values.max()),
            percentile_1=float(np.percentile(values, 1)),
            percentile_99=float(np.percentile(values, 99)),
        )
    return {
        "schema_version": policy["schema_version"],
        "contract_version": policy["contract_version"],
        "dataset_id": policy["dataset_id"],
        "prepared_source_sha256": prepared_hash,
        "source_scope": policy["source_scope"],
        "generation_policy": policy["policy"],
        "feature_order": list(MODEL_FEATURE_COLUMNS),
        "features": features,
    }


def write_input_domain_contract(document, output_path):
    serialized = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    Path(output_path).write_text(serialized + "\n", encoding="utf-8")
