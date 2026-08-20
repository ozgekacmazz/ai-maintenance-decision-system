import json

from bakim_ml.data_contract import MODEL_FEATURE_COLUMNS
from bakim_ml.input_domain import generate_input_domain_contract


def test_generated_contract_uses_train_statistics_and_is_deterministic():
    # Proje metadata/policy dosyalarıyla aynı üretim iki kez aynı sonucu vermelidir.
    dataset = "data/processed/ai4i2020_prepared.csv"
    policy = "data/metadata/input_domain_policy.json"
    first = generate_input_domain_contract(dataset, policy)
    second = generate_input_domain_contract(dataset, policy)

    assert first == second
    assert tuple(first["feature_order"]) == MODEL_FEATURE_COLUMNS
    assert first["source_scope"] == "train_split"
    assert len(first["prepared_source_sha256"]) == 64
    assert json.dumps(first, allow_nan=False)
