from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor


@dataclass(frozen=True)
class SaglikDurumu:
    durum: str
    servis: str
    veritabani: str
    migrationlar: str = "uygun"
    model_dosyalari: str = "hazir"


def saglik_durumunu_getir() -> SaglikDurumu:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return SaglikDurumu(
            "kullanilamiyor", "backend", "baglanti_yok", "bilinmiyor", "bilinmiyor"
        )

    executor = MigrationExecutor(connection)
    migrationlar = (
        "uygun"
        if not executor.migration_plan(executor.loader.graph.leaf_nodes())
        else "bekliyor"
    )
    required_paths = (
        settings.MODEL_ARTIFACT_PATH,
        settings.MODEL_METADATA_PATH,
        settings.FAILURE_TYPE_MODEL_ARTIFACT_PATH,
        settings.FAILURE_TYPE_MODEL_METADATA_PATH,
        settings.INPUT_DOMAIN_CONTRACT_PATH,
    )
    model_dosyalari = (
        "hazir" if all(Path(path).is_file() for path in required_paths) else "eksik"
    )
    durum = (
        "hazir"
        if migrationlar == "uygun" and model_dosyalari == "hazir"
        else "kullanilamiyor"
    )
    return SaglikDurumu(durum, "backend", "bagli", migrationlar, model_dosyalari)
