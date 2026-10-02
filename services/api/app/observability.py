"""Structured request logging and Prometheus metrics."""

import json
import logging
import time

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "howl_api_requests_total",
    "Total HTTP requests handled by the API",
    ("method", "path", "status"),
)
REQUEST_DURATION = Histogram(
    "howl_api_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)
ACTIVE_REQUESTS = Gauge(
    "howl_api_active_requests",
    "Number of HTTP requests currently being processed",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("howl")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def request_timer() -> float:
    return time.perf_counter()
