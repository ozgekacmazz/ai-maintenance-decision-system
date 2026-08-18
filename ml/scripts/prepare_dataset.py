import argparse

from bakim_ml.features import ReplayConfig
from bakim_ml.prepare import prepare_dataset


def main():
    parser = argparse.ArgumentParser(
        description="AI4I verisini deterministik olarak hazırla."
    )
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--metadata")
    parser.add_argument("--machine-count", type=int, default=20)
    parser.add_argument("--interval-minutes", type=int, default=5)
    args = parser.parse_args()
    frame, metadata = prepare_dataset(
        args.input,
        args.output,
        args.metadata,
        ReplayConfig(
            machine_count=args.machine_count, interval_minutes=args.interval_minutes
        ),
    )
    summary = (
        f"Hazırlama tamamlandı: {len(frame)} satır, "
        f"{len(frame.columns)} sütun, sürüm {metadata['pipeline_version']}."
    )
    print(summary)


if __name__ == "__main__":
    main()
