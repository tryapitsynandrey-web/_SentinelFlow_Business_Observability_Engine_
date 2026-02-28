import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJSONFormatter(logging.Formatter):
    """
    Production-grade JSON structured formatter.
    """

    RESERVED_ATTRS = {
        "name", "msg", "args", "levelname", "levelno",
        "pathname", "filename", "module", "exc_info",
        "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process",
    }

    def format(self, record: logging.LogRecord) -> str:

        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Include all extra attributes dynamically
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                try:
                    json.dumps(value)  # check serializable
                    log_data[key] = value
                except TypeError:
                    log_data[key] = str(value)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        try:
            return json.dumps(log_data)
        except Exception:
            # Fallback safety
            return json.dumps({
                "timestamp": log_data["timestamp"],
                "level": "ERROR",
                "message": "Failed to serialize log record",
            })


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configures root logger once during application bootstrap.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Returns logger instance.
    Assumes configure_logging() has already been called.
    """
    return logging.getLogger(name)