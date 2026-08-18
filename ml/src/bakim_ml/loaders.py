from hashlib import sha256
from pathlib import Path

import pandas as pd

from .data_contract import (
    BINARY_TARGET_COLUMNS,
    CANONICAL_COLUMNS,
    DERIVED_COLUMNS,
    RAW_COLUMNS,
    canonicalize_columns,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_PATH = REPO_ROOT / "data" / "raw" / "ai4i2020.csv"
DEFAULT_PREPARED_PATH = REPO_ROOT / "data" / "processed" / "ai4i2020_prepared.csv"


class DatasetLoadError(Exception):
    pass


def file_sha256(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_path(path=None):
    candidate = Path(path) if path else DEFAULT_RAW_PATH
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def load_dataset(path=None, *, expected_sha256=None):
    source = resolve_path(path)
    if not source.is_file():
        raise DatasetLoadError("Veri dosyası bulunamadı; data/raw altına yerleştirin.")
    if expected_sha256 and file_sha256(source).lower() != expected_sha256.lower():
        raise DatasetLoadError("Veri dosyası checksum doğrulamasından geçemedi.")
    try:
        frame = pd.read_csv(
            source,
            encoding="utf-8",
            sep=",",
            dtype={"Product ID": "string", "Type": "string"},
        )
    except (UnicodeError, pd.errors.ParserError) as exc:
        raise DatasetLoadError("CSV güvenli biçimde okunamadı.") from exc
    missing = sorted(set(RAW_COLUMNS) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(RAW_COLUMNS))
    if missing:
        raise DatasetLoadError(f"Zorunlu sütunlar eksik: {', '.join(missing)}")
    numeric_raw = [name for name in RAW_COLUMNS if name not in {"Product ID", "Type"}]
    try:
        for column in numeric_raw:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
    except (ValueError, TypeError) as exc:
        raise DatasetLoadError("Sayısal sütunda geçersiz değer bulundu.") from exc
    canonical = canonicalize_columns(frame)
    for column in BINARY_TARGET_COLUMNS:
        if not canonical[column].dropna().isin((0, 1)).all():
            raise DatasetLoadError("Binary hedef sütununda 0/1 dışında değer bulundu.")
    canonical.attrs["unexpected_columns"] = extra
    return canonical


def load_prepared_dataset(path=None, *, expected_sha256=None):
    source = resolve_path(path) if path else DEFAULT_PREPARED_PATH
    if not source.is_file():
        raise DatasetLoadError("Hazırlanmış veri dosyası bulunamadı.")
    if expected_sha256 and file_sha256(source).lower() != expected_sha256.lower():
        raise DatasetLoadError("Veri dosyası checksum doğrulamasından geçemedi.")
    try:
        frame = pd.read_csv(
            source,
            encoding="utf-8",
            sep=",",
            dtype={"urun_kodu": "string", "urun_tipi": "string"},
        )
    except (UnicodeError, pd.errors.ParserError) as exc:
        raise DatasetLoadError("Hazırlanmış CSV güvenli biçimde okunamadı.") from exc
    required = {
        *CANONICAL_COLUMNS,
        *DERIVED_COLUMNS,
        "machine_id",
        "timestamp",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DatasetLoadError(f"Zorunlu sütunlar eksik: {', '.join(missing)}")
    for column in BINARY_TARGET_COLUMNS:
        if not frame[column].dropna().isin((0, 1)).all():
            raise DatasetLoadError("Binary hedef sütununda 0/1 dışında değer bulundu.")
    return frame
