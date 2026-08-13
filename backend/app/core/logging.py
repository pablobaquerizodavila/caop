"""Logging estructurado en JSON con correlation_id."""

import logging

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # versiones antiguas de python-json-logger
    from pythonjsonlogger.jsonlogger import JsonFormatter

from app.core.config import settings
from app.core.correlation import get_correlation_id


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s")
    )
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
