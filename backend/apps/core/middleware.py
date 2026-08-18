import json
import logging
import re
import time
import uuid

from apps.core.error_contract import json_hata_response

logger = logging.getLogger("api.request")
TRACE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class TraceIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        baslangic = time.perf_counter()
        gelen_trace = request.headers.get("X-Trace-ID", "")
        request.trace_id = (
            gelen_trace if TRACE_PATTERN.fullmatch(gelen_trace) else str(uuid.uuid4())
        )

        response = self.get_response(request)
        if request.path.startswith("/api/") and response.status_code >= 400:
            response = self._gerekirse_standartlastir(response, request.trace_id)
        response["X-Trace-ID"] = request.trace_id

        logger.info(
            "api_request_completed",
            extra={
                "event": "api_request_completed",
                "trace_id": request.trace_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - baslangic) * 1000, 2),
            },
        )
        return response

    @staticmethod
    def _gerekirse_standartlastir(response, trace_id):
        try:
            mevcut = json.loads(response.content)
        except (ValueError, TypeError, UnicodeDecodeError):
            mevcut = None
        if isinstance(mevcut, dict) and "hata" in mevcut:
            return response
        return json_hata_response(status_code=response.status_code, trace_id=trace_id)
