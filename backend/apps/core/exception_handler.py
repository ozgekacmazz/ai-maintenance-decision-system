import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.error_contract import hata_govdesi
from apps.core.exceptions import HizmetKullanilamiyorHatasi, KaynakCakismasiHatasi

logger = logging.getLogger("api.exception")


def _guvenli_json(deger):
    if isinstance(deger, dict):
        return {str(anahtar): _guvenli_json(alt) for anahtar, alt in deger.items()}
    if isinstance(deger, (list, tuple)):
        return [_guvenli_json(alt) for alt in deger]
    return str(deger)


def standart_exception_handler(exc, context):
    request = context.get("request")
    trace_id = getattr(request, "trace_id", "bilinmiyor")

    if isinstance(exc, KaynakCakismasiHatasi):
        return Response(
            hata_govdesi(status_code=409, trace_id=trace_id),
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, HizmetKullanilamiyorHatasi):
        logger.error(
            "Kontrollü hizmet hatası.",
            extra={
                "event": "service_unavailable",
                "trace_id": trace_id,
                "exception_type": type(exc).__name__,
            },
        )
        return Response(
            hata_govdesi(
                status_code=503,
                trace_id=trace_id,
                kod=exc.kod,
                mesaj=exc.mesaj,
            ),
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.error(
            "Beklenmeyen API hatası güvenli biçimde yakalandı.",
            extra={
                "event": "unexpected_api_exception",
                "trace_id": trace_id,
                "exception_type": type(exc).__name__,
            },
        )
        return Response(
            hata_govdesi(status_code=500, trace_id=trace_id),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    alanlar = {}
    if isinstance(exc, exceptions.ValidationError):
        alanlar = _guvenli_json(response.data)
        mesaj = "Gönderilen bilgilerde doğrulama hataları var."
    else:
        mesaj = None

    response.data = hata_govdesi(
        status_code=response.status_code,
        trace_id=trace_id,
        alanlar=alanlar,
        mesaj=mesaj,
    )

    if response.status_code == 401 and request.path.endswith("/api/auth/refresh/"):
        from apps.kullanicilar.cookies import refresh_cookie_sil

        refresh_cookie_sil(response)
    return response
