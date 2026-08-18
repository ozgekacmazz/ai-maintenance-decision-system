from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from .data_contract import CANONICAL_COLUMNS, DERIVED_COLUMNS


@dataclass(frozen=True)
class ReplayConfig:
    machine_count: int = 20
    interval_minutes: int = 5
    start_time: datetime = datetime(2020, 1, 1, tzinfo=UTC)

    def __post_init__(self):
        if self.machine_count < 1 or self.interval_minutes < 1:
            raise ValueError("Makine sayısı ve aralık pozitif olmalıdır.")
        if self.start_time.tzinfo is None:
            raise ValueError("Başlangıç zamanı timezone-aware olmalıdır.")


def add_engineered_features(frame):
    result = frame.copy(deep=True)
    result["proses_hava_sicaklik_farki_k"] = (
        result["proses_sicakligi_k"] - result["hava_sicakligi_k"]
    )
    result["acisal_hiz_rad_s"] = 2 * np.pi * result["donus_hizi_rpm"] / 60
    result["mekanik_guc_w"] = result["tork_nm"] * result["acisal_hiz_rad_s"]
    if not np.isfinite(result[list(DERIVED_COLUMNS)].to_numpy(dtype=float)).all():
        raise ValueError("Türetilmiş özellikler sonlu değil.")
    return result


def add_replay_fields(frame, config=None):
    config = config or ReplayConfig()
    result = frame.copy(deep=True)
    positions = np.arange(len(result))
    result["machine_id"] = [
        f"M-{index % config.machine_count + 1:03d}" for index in positions
    ]
    result["timestamp"] = [
        config.start_time
        + timedelta(
            minutes=int(config.interval_minutes * (index // config.machine_count))
        )
        for index in positions
    ]
    return result


def prepare_frame(frame, config=None):
    result = add_replay_fields(add_engineered_features(frame), config)
    return result[[*CANONICAL_COLUMNS, *DERIVED_COLUMNS, "machine_id", "timestamp"]]
