import argparse
import json

from bakim_ml.training import train_binary_model


def main():
    parser = argparse.ArgumentParser(description="Binary makine arızası modelini eğit.")
    parser.add_argument("--input")
    parser.add_argument("--artifact")
    parser.add_argument("--metadata")
    args = parser.parse_args()
    metadata = train_binary_model(args.input, args.artifact, args.metadata)
    summary = {
        "model_version": metadata["model_version"],
        "selected_model": metadata["selected_model"],
        "threshold": metadata["threshold"],
        "test_metrics": metadata["test_metrics"],
        "artifact_sha256": metadata["artifact"]["sha256"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
