import argparse
import json

from bakim_ml.data_contract import FAILURE_TYPE_COLUMNS
from bakim_ml.loaders import file_sha256, load_dataset, resolve_path
from bakim_ml.validation import validate_quality


def main():
    parser = argparse.ArgumentParser(
        description="AI4I veri setini güvenli biçimde profille."
    )
    parser.add_argument("--input")
    args = parser.parse_args()
    frame = load_dataset(args.input)
    failure_sum = frame[list(FAILURE_TYPE_COLUMNS)].sum(axis=1)
    result = {
        "rows": len(frame),
        "columns": len(frame.columns),
        "sha256": file_sha256(resolve_path(args.input)),
        "null_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
        "machine_failures": int(frame["makine_arizasi"].sum()),
        "failure_types": {
            name: int(frame[name].sum()) for name in FAILURE_TYPE_COLUMNS
        },
        "multiple_failure_types": int((failure_sum > 1).sum()),
        "quality": [issue.to_dict() for issue in validate_quality(frame).issues],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
