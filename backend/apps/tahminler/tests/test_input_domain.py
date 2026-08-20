import json

import pytest
from django.test import override_settings

from apps.tahminler.exceptions import ModelHizmetiHatasi
from apps.tahminler.input_domain import (
    frontend_input_domain_contract,
    input_domain_cache_sifirla,
    input_domain_contract_getir,
)


@pytest.fixture(autouse=True)
def reset_cache():
    input_domain_cache_sifirla()
    yield
    input_domain_cache_sifirla()


def test_frontend_contract_is_allowlisted_and_versioned():
    result = frontend_input_domain_contract()
    assert result["contract_version"] == "ai4i-input-domain-1.0.0"
    assert set(result["fields"]) == {
        "hava_sicakligi_k",
        "proses_sicakligi_k",
        "donus_hizi_rpm",
        "tork_nm",
        "takim_asinmasi_dk",
    }
    assert "observed_min" not in result["fields"]["hava_sicakligi_k"]


def test_invalid_contract_fails_closed(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"contract_version": "broken"}), encoding="utf-8")
    with override_settings(INPUT_DOMAIN_CONTRACT_PATH=path):
        with pytest.raises(ModelHizmetiHatasi) as error:
            input_domain_contract_getir()
    assert error.value.kod == "INPUT_DOMAIN_CONTRACT_KULLANILAMIYOR"
