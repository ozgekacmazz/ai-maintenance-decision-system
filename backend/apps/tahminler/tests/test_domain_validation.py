from unittest.mock import patch

import pytest
from rest_framework.exceptions import ValidationError

from apps.tahminler.domain_validation import model_girdilerini_dogrula
from apps.tahminler.services import _ozellikleri_hazirla


def get_valid_payload():
    return {
        "urun_tipi": "L",
        "hava_sicakligi_k": 298.1,
        "proses_sicakligi_k": 308.6,
        "donus_hizi_rpm": 1551,
        "tork_nm": 42.8,
        "takim_asinmasi_dk": 0,
    }


def test_valid_payload_passes():
    payload = get_valid_payload()
    result = model_girdilerini_dogrula(payload)
    assert result == payload


def test_regression_ood_temperature_29_1_k_rejected():
    payload = get_valid_payload()
    payload["hava_sicakligi_k"] = 29.1
    payload["proses_sicakligi_k"] = 30.6

    with pytest.raises(ValidationError) as exc_info:
        model_girdilerini_dogrula(payload)

    errors = exc_info.value.detail
    assert "hava_sicakligi_k" in errors
    assert "fiziksel sınırlar dışında" in str(errors["hava_sicakligi_k"][0])


def test_ood_temperature_285_k_rejected():
    payload = get_valid_payload()
    payload["hava_sicakligi_k"] = 285.0
    payload["proses_sicakligi_k"] = 308.6

    with pytest.raises(ValidationError) as exc_info:
        model_girdilerini_dogrula(payload)

    errors = exc_info.value.detail
    assert "hava_sicakligi_k" in errors
    assert "çalışma aralığının dışında" in str(errors["hava_sicakligi_k"][0])


def test_nan_infinity_rejected():
    for bad_val in [float("nan"), float("inf"), float("-inf")]:
        payload = get_valid_payload()
        payload["hava_sicakligi_k"] = bad_val
        with pytest.raises(ValidationError):
            model_girdilerini_dogrula(payload)


def test_negative_rpm_and_tork_rejected():
    payload = get_valid_payload()
    payload["donus_hizi_rpm"] = -100
    with pytest.raises(ValidationError):
        model_girdilerini_dogrula(payload)

    payload = get_valid_payload()
    payload["tork_nm"] = -5.0
    with pytest.raises(ValidationError):
        model_girdilerini_dogrula(payload)


def test_invalid_product_type_rejected():
    payload = get_valid_payload()
    payload["urun_tipi"] = "INVALID"
    with pytest.raises(ValidationError):
        model_girdilerini_dogrula(payload)


def test_cross_field_temperature_difference_rejected():
    payload = get_valid_payload()
    # Air temp is valid (298.1), but process temp is equal to air temp (diff = 0)
    payload["proses_sicakligi_k"] = 298.1
    with pytest.raises(ValidationError) as exc_info:
        model_girdilerini_dogrula(payload)
    assert "proses_sicakligi_k" in exc_info.value.detail


def test_model_predict_proba_not_called_on_ood_payload():
    payload = get_valid_payload()
    payload["hava_sicakligi_k"] = 29.1

    with patch("bakim_ml.modeling.feature_frame") as mock_ff:
        with pytest.raises(ValidationError):
            _ozellikleri_hazirla(payload)
        mock_ff.assert_not_called()
