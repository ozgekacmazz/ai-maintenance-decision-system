import argparse

from bakim_ml.input_domain import (
    generate_input_domain_contract,
    write_input_domain_contract,
)
from bakim_ml.loaders import REPO_ROOT


def main():
    parser = argparse.ArgumentParser(description="Sürümlü input-domain contract üret.")
    parser.add_argument(
        "--dataset", default=REPO_ROOT / "data/processed/ai4i2020_prepared.csv"
    )
    parser.add_argument(
        "--policy", default=REPO_ROOT / "data/metadata/input_domain_policy.json"
    )
    parser.add_argument(
        "--output", default=REPO_ROOT / "data/metadata/input_domain_contract.json"
    )
    args = parser.parse_args()
    contract = generate_input_domain_contract(args.dataset, args.policy)
    write_input_domain_contract(contract, args.output)
    print(f"Input-domain contract üretildi: {contract['contract_version']}")


if __name__ == "__main__":
    main()
