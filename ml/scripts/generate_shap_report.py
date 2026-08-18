import argparse
import json

from bakim_ml.shap_report import DEFAULT_OUTPUT, generate_shap_analysis


def main():
    parser = argparse.ArgumentParser(
        description="Validation örneğinden deterministik global SHAP raporu üret."
    )
    parser.add_argument("--sample-size", type=int, default=25)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    document = generate_shap_analysis(
        sample_size=args.sample_size, output_path=args.output
    )
    print(
        json.dumps(
            {
                "analysis_version": document["analysis_version"],
                "sample_size": document["sample"]["size"],
                "fingerprint": document["fingerprint"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
