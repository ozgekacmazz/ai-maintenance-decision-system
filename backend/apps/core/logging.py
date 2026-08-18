import json
import logging


class GuvenliJsonFormatter(logging.Formatter):
    ALANLAR = (
        "event",
        "trace_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "exception_type",
    )

    def format(self, record):
        veri = {
            alan: getattr(record, alan)
            for alan in self.ALANLAR
            if getattr(record, alan, None) is not None
        }
        if not veri:
            veri = {"event": "application_log", "level": record.levelname}
        return json.dumps(veri, ensure_ascii=False)
