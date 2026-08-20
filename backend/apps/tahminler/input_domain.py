import json
import math
import threading
from pathlib import Path
from types import MappingProxyType

from bakim_ml.data_contract import ALLOWED_PRODUCT_TYPES, MODEL_FEATURE_COLUMNS, UNITS
from django.conf import settings

from apps.tahminler.exceptions import ModelHizmetiHatasi

_cache_lock = threading.Lock()
_cached_contract = None
_cached_path = None


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _checksum(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def _contract_dogrula(document):
    required = {
        "schema_version",
        "contract_version",
        "dataset_id",
        "prepared_source_sha256",
        "source_scope",
        "generation_policy",
        "feature_order",
        "features",
    }
    if not isinstance(document, dict) or not required <= document.keys():
        raise ValueError("Contract üst bilgileri eksik.")
    if not document["contract_version"] or not _checksum(
        document["prepared_source_sha256"]
    ):
        raise ValueError("Contract sürümü veya SHA-256 geçersiz.")
    if tuple(document["feature_order"]) != MODEL_FEATURE_COLUMNS:
        raise ValueError("Contract feature sırası modelle uyumsuz.")
    features = document["features"]
    if not isinstance(features, dict) or set(features) != set(MODEL_FEATURE_COLUMNS):
        raise ValueError("Contract feature kümesi modelle uyumsuz.")
    for name, config in features.items():
        if not isinstance(config, dict) or config.get("dtype") not in {
            "float",
            "string",
        }:
            raise ValueError(f"{name} şeması geçersiz.")
        expected_unit = "category" if name == "urun_tipi" else UNITS[name]
        if config.get("unit") != expected_unit:
            raise ValueError(f"{name} birimi geçersiz.")
        if name == "urun_tipi":
            if set(config.get("allowed", ())) != set(ALLOWED_PRODUCT_TYPES):
                raise ValueError("Ürün tipi sözleşmesi geçersiz.")
            continue
        for key in ("observed_min", "observed_max", "percentile_1", "percentile_99"):
            value = config.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name}.{key} sonlu sayı olmalıdır.")
        if config["observed_min"] > config["observed_max"]:
            raise ValueError(f"{name} observed sınırları geçersiz.")
        if not (
            config["observed_min"]
            <= config["percentile_1"]
            <= config["percentile_99"]
            <= config["observed_max"]
        ):
            raise ValueError(f"{name} percentile sırası geçersiz.")
        if config.get("api_field"):
            physical = config.get("physical_min"), config.get("physical_max")
            if (
                not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in physical
                )
                or physical[0] >= physical[1]
            ):
                raise ValueError(f"{name} physical sınırları geçersiz.")
        if "supported_min" in config or "supported_max" in config:
            low, high = config.get("supported_min"), config.get("supported_max")
            if (
                not all(
                    isinstance(x, (int, float))
                    and not isinstance(x, bool)
                    and math.isfinite(x)
                    for x in (low, high)
                )
                or low >= high
            ):
                raise ValueError(f"{name} supported sınırları geçersiz.")
            if config.get("api_field") and not physical[0] <= low < high <= physical[1]:
                raise ValueError(
                    f"{name} supported sınırları physical sınırları aşıyor."
                )
    return _freeze(document)


def input_domain_contract_getir(*, path=None):
    global _cached_contract, _cached_path
    resolved = str(path or settings.INPUT_DOMAIN_CONTRACT_PATH)
    if _cached_contract is not None and _cached_path == resolved:
        return _cached_contract
    with _cache_lock:
        if _cached_contract is None or _cached_path != resolved:
            try:
                document = json.loads(Path(resolved).read_text(encoding="utf-8"))
                loaded = _contract_dogrula(document)
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
                TypeError,
            ) as exc:
                raise ModelHizmetiHatasi(
                    "Input-domain sözleşmesi kullanılamıyor.",
                    kod="INPUT_DOMAIN_CONTRACT_KULLANILAMIYOR",
                ) from exc
            _cached_contract, _cached_path = loaded, resolved
    return _cached_contract


def input_domain_cache_sifirla():
    global _cached_contract, _cached_path
    with _cache_lock:
        _cached_contract = _cached_path = None


def frontend_input_domain_contract():
    contract = input_domain_contract_getir()
    fields = {}
    for config in contract["features"].values():
        api_field = config.get("api_field")
        if not api_field or "supported_min" not in config:
            continue
        fields[api_field] = {
            "canonical_unit": config["unit"],
            "display_unit": config.get("display_unit", config["unit"]),
            "supported_min": config["supported_min"],
            "supported_max": config["supported_max"],
        }
    return {"contract_version": contract["contract_version"], "fields": fields}
