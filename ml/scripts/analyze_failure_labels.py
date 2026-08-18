import argparse
import json
from pathlib import Path

from bakim_ml.failure_labels import (
    DEFAULT_METADATA,
    build_analysis_metadata,
    write_analysis_metadata,
)
from bakim_ml.loaders import (
    DEFAULT_PREPARED_PATH,
    REPO_ROOT,
    file_sha256,
    load_prepared_dataset,
)

DEFAULT_PREPARED_METADATA = REPO_ROOT / "data" / "metadata" / "ai4i2020_prepared.json"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="AI4I arıza tipi etiketlerini analiz et."
    )
    parser.add_argument("--input", default=str(DEFAULT_PREPARED_PATH))
    parser.add_argument("--prepared-metadata", default=str(DEFAULT_PREPARED_METADATA))
    parser.add_argument("--output", default=str(DEFAULT_METADATA))
    parser.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    prepared_metadata = json.loads(
        Path(args.prepared_metadata).read_text(encoding="utf-8")
    )
    frame = load_prepared_dataset(input_path, expected_sha256=args.expected_sha256)
    document = build_analysis_metadata(
        frame,
        source_sha256=prepared_metadata["source_sha256"],
        prepared_source_sha256=file_sha256(input_path),
    )
    write_analysis_metadata(document, args.output)
    print(
        "Analiz tamamlandı: "
        f"{document['total_rows']} satır, "
        f"{document['rows_with_multiple_labels']} multi-label kayıt, "
        f"fingerprint {document['analysis_fingerprint_sha256']}."
    )
    print(f"Çıktı: {Path(args.output)}")
    return document


if __name__ == "__main__":
    main()
