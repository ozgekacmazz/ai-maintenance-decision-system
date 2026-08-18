from dataclasses import dataclass

from django.db import DatabaseError, connection


@dataclass(frozen=True)
class SaglikDurumu:
    durum: str
    servis: str
    veritabani: str


def saglik_durumunu_getir() -> SaglikDurumu:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return SaglikDurumu("kullanilamiyor", "backend", "baglanti_yok")
    return SaglikDurumu("hazir", "backend", "bagli")
