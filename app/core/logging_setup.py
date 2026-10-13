import json
import logging
import traceback


class JSONLogFormatter(logging.Formatter):
    """One JSON object per log line: filterable in Vercel's log viewer."""

    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("request_id", "path", "method", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            # Last line (the actual error) first, so truncated viewers
            # still show the cause; full traceback after.
            tb = "".join(traceback.format_exception(*record.exc_info))
            payload["error"] = tb.strip().splitlines()[-1][:300]
            payload["exception"] = tb
        return json.dumps(payload)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    return logging.getLogger("bstm")
