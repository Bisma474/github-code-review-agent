import json
import logging
import sys
from logging import Handler, LogRecord
from typing import Any

from app.core.config import get_settings

settings = get_settings()


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for production logs.
    Formats logs as JSON objects with timestamp, level, module, message, and any extra fields.
    """

    def format(self, record: LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack_trace"] = self.formatStack(record.stack_info)

        for key, value in record.__dict__.items():
            if key not in ["asctime", "message", "created", "filename", "funcName",
                          "levelname", "lineno", "module", "msecs", "msg", "pathname",
                          "process", "processName", "relativeCreated", "thread",
                          "threadName", "exc_info", "exc_text", "stack_info"]:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """
    Human-readable formatter with color codes for development.
    """

    COLORS = {
        logging.DEBUG: "\033[36m",      # Cyan
        logging.INFO: "\033[32m",       # Green
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }

    RESET = "\033[0m"

    def format(self, record: LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        levelname = f"{color}{record.levelname}{self.RESET}"

        log_message = record.getMessage()

        if record.exc_info:
            log_message += "\n" + self.formatException(record.exc_info)

        return f"{levelname} - {log_message}"


def setup_logging() -> None:
    """
    Configure the root logger based on APP_ENV.
    - Development: Console with color
    - Production: Console with JSON formatting
    """

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        return

    if settings.APP_ENV == "production":
        formatter = JsonFormatter()
        console_handler = logging.StreamHandler(sys.stdout)
    else:
        formatter = ColorFormatter()
        console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with the given name.

    Args:
        name: Logger name, typically __name__ of the module

    Returns:
        Configured logger instance
    """

    setup_logging()
    return logging.getLogger(name)