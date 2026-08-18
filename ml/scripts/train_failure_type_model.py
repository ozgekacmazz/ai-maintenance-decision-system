import argparse

from bakim_ml.failure_type_training import train_failure_type_model


def main():
    parser = argparse.ArgumentParser(
        description="Dört fiziksel arıza tipi için multi-label modeli eğit."
    )
    parser.add_argument("--input")
    parser.add_argument("--artifact")
    parser.add_argument("--metadata")
    args = parser.parse_args()
    metadata = train_failure_type_model(args.input, args.artifact, args.metadata)
    print(
        f"Seçilen aday: {metadata['selected_candidate']}; "
        f"validation macro PR-AUC: "
        f"{metadata['candidate_validation'][metadata['selected_candidate']]['validation_macro_pr_auc']:.4f}."
    )
    print(f"Threshold'lar: {metadata['thresholds']}")
    print(f"Artefakt: {metadata['artifact']['relative_path']}")


if __name__ == "__main__":
    main()
