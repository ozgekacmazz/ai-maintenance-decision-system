from dataclasses import asdict, dataclass

import numpy as np

from .data_contract import (
    ALLOWED_PRODUCT_TYPES,
    BINARY_TARGET_COLUMNS,
    CANONICAL_COLUMNS,
    FAILURE_TYPE_COLUMNS,
    NUMERIC_SENSOR_COLUMNS,
)


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str
    affected_rows: int

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class QualityResult:
    issues: tuple[QualityIssue, ...]

    @property
    def passed(self):
        return not any(issue.severity == "error" for issue in self.issues)


def validate_quality(frame):
    issues = []

    def add(severity, code, message, count):
        issues.append(QualityIssue(severity, code, message, int(count)))

    if frame.empty:
        add("error", "EMPTY_DATASET", "Veri seti boş.", 0)
        return QualityResult(tuple(issues))
    missing_columns = set(CANONICAL_COLUMNS) - set(frame.columns)
    if missing_columns:
        add("error", "MISSING_COLUMNS", "Zorunlu sütunlar eksik.", len(missing_columns))
        return QualityResult(tuple(issues))
    unexpected = set(frame.columns) - set(CANONICAL_COLUMNS)
    if unexpected:
        add(
            "warning",
            "UNEXPECTED_COLUMNS",
            "Beklenmeyen sütunlar korunarak raporlandı.",
            len(unexpected),
        )
    null_rows = frame[list(CANONICAL_COLUMNS)].isna().any(axis=1).sum()
    if null_rows:
        add("error", "NULL_VALUES", "Zorunlu alanlarda null değer var.", null_rows)
    duplicate_udi = frame["udi"].duplicated(keep=False).sum()
    if duplicate_udi:
        add("error", "DUPLICATE_UDI", "UDI değerleri benzersiz değil.", duplicate_udi)
    duplicate_rows = frame.duplicated(keep=False).sum()
    if duplicate_rows:
        add("error", "DUPLICATE_ROWS", "Tam duplicate satırlar var.", duplicate_rows)
    for column in (*NUMERIC_SENSOR_COLUMNS, *BINARY_TARGET_COLUMNS, "udi"):
        invalid = (
            ~frame[column].map(
                lambda value: isinstance(value, (int, float, np.integer, np.floating))
            )
        ).sum()
        if invalid:
            add("error", "INVALID_NUMERIC", f"{column} sayısal değil.", invalid)
    invalid_types = (~frame["urun_tipi"].isin(ALLOWED_PRODUCT_TYPES)).sum()
    if invalid_types:
        add("error", "UNKNOWN_PRODUCT_TYPE", "Bilinmeyen ürün tipi var.", invalid_types)
    checks = (
        (
            frame["hava_sicakligi_k"] <= 0,
            "INVALID_AIR_TEMPERATURE",
            "Hava sıcaklığı mutlak sıfırın üzerinde olmalı.",
        ),
        (
            frame["proses_sicakligi_k"] <= 0,
            "INVALID_PROCESS_TEMPERATURE",
            "Proses sıcaklığı mutlak sıfırın üzerinde olmalı.",
        ),
        (
            frame["donus_hizi_rpm"] <= 0,
            "INVALID_ROTATIONAL_SPEED",
            "Dönüş hızı pozitif olmalı.",
        ),
        (frame["tork_nm"] < 0, "INVALID_TORQUE", "Tork negatif olamaz."),
        (
            frame["takim_asinmasi_dk"] < 0,
            "INVALID_TOOL_WEAR",
            "Takım aşınması negatif olamaz.",
        ),
    )
    for mask, code, message in checks:
        if count := mask.sum():
            add("error", code, message, count)
    failure_sum = frame[list(FAILURE_TYPE_COLUMNS)].sum(axis=1)
    orphan_type = ((frame["makine_arizasi"] == 0) & (failure_sum > 0)).sum()
    missing_type = ((frame["makine_arizasi"] == 1) & (failure_sum == 0)).sum()
    multi_type = (failure_sum > 1).sum()
    for count, code, message in (
        (
            orphan_type,
            "FAILURE_TYPE_WITHOUT_FAILURE",
            "Ana hedef 0 iken arıza tipi pozitiftir.",
        ),
        (missing_type, "FAILURE_WITHOUT_TYPE", "Ana hedef 1 iken arıza tipi yoktur."),
        (
            multi_type,
            "MULTIPLE_FAILURE_TYPES",
            "Birden fazla arıza tipi olan satırlar vardır.",
        ),
    ):
        if count:
            add("warning", code, message, count)
    return QualityResult(tuple(issues))


def require_quality(frame):
    result = validate_quality(frame)
    if not result.passed:
        raise ValueError("Veri kalite kapısı başarısız.")
    return result
