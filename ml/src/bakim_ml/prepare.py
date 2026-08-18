import json
import os
from datetime import UTC, datetime

from .data_contract import PIPELINE_VERSION
from .features import ReplayConfig, prepare_frame
from .loaders import REPO_ROOT, file_sha256, load_dataset, resolve_path
from .validation import require_quality

DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "ai4i2020_prepared.csv"
DEFAULT_METADATA = REPO_ROOT / "data" / "metadata" / "ai4i2020_prepared.json"


def prepare_dataset(source=None, output=None, metadata=None, config=None):
    source_path = resolve_path(source)
    output_path = resolve_path(output) if output else DEFAULT_OUTPUT
    metadata_path = resolve_path(metadata) if metadata else DEFAULT_METADATA
    frame = load_dataset(source_path)
    quality = require_quality(frame)
    config = config or ReplayConfig()
    prepared = prepare_frame(frame, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        prepared.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    document = {
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source": "data/raw/ai4i2020.csv",
        "source_sha256": file_sha256(source_path),
        "rows": len(prepared),
        "columns": len(prepared.columns),
        "config": {
            "machine_count": config.machine_count,
            "interval_minutes": config.interval_minutes,
            "start_time": config.start_time.isoformat(),
        },
        "quality_warnings": [
            issue.to_dict() for issue in quality.issues if issue.severity == "warning"
        ],
    }
    metadata_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return prepared, document
