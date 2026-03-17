"""SiliconDNA Utilities - Structured & Colored Logging"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


COLORS = {
    "reset": "\033[0m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bold": "\033[1m",
}


class StructuredLogRecord(logging.LogRecord):
    """Extended log record with structured data for ML ingestion."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.structured_data: Dict[str, Any] = {}

    def set_structured_data(self, **kwargs):
        """Add structured data to the log record."""
        self.structured_data.update(kwargs)

    def get_structured_dict(self) -> Dict[str, Any]:
        """Get log record as structured dictionary for ML."""
        return {
            "timestamp": self.created,
            "level": self.levelname,
            "logger": self.name,
            "message": self.getMessage(),
            "module": self.module,
            "function": self.funcName,
            "line": self.lineno,
            "structured_data": self.structured_data,
        }


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for algorithmic ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record, StructuredLogRecord):
            data = record.get_structured_dict()
        else:
            data = {
                "timestamp": record.created,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
        return json.dumps(data)


class ColoredFormatter(logging.Formatter):
    """Human-readable colored terminal output."""

    LEVEL_COLORS = {
        logging.DEBUG: "cyan",
        logging.INFO: "green",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "bold red",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, "white")
        record.levelname = f"{COLORS[color]}{record.levelname}{COLORS['reset']}"
        record.msg = f"{COLORS[color]}{record.msg}{COLORS['reset']}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    colored: bool = True,
    json_file: Optional[str] = None,
) -> logging.Logger:
    """
    Setup logging with colored terminal output and optional JSON file for ML.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        colored: Enable colored terminal output
        json_file: Optional path to JSON log file for ML ingestion
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if colored:
        console_handler.setFormatter(
            ColoredFormatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    handlers = [console_handler]

    if json_file:
        json_handler = logging.FileHandler(json_file)
        json_handler.setLevel(log_level)
        json_handler.setFormatter(StructuredJSONFormatter())
        handlers.append(json_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in handlers:
        root_logger.addHandler(handler)

    return root_logger


class SiliconDNALogger:
    """
    Enhanced logger with structured logging for ML ingestion.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _create_structured_record(
        self, level: int, msg: str, **structured_data
    ) -> StructuredLogRecord:
        """Create a structured log record."""
        record = StructuredLogRecord(
            name=self.name,
            level=level,
            msg=msg,
            pathname="",
            filename="",
            lineno=0,
            args=(),
            exc_info=None,
        )
        record.set_structured_data(**structured_data)
        return record

    def log_command(
        self,
        command_name: str,
        user_id: str,
        guild_id: Optional[str],
        execution_time_ms: float,
        success: bool,
        **kwargs,
    ):
        """Log command execution with structured data for ML."""
        structured_data = {
            "event_type": "command_execution",
            "command_name": command_name,
            "user_id": user_id,
            "guild_id": guild_id,
            "execution_time_ms": execution_time_ms,
            "success": success,
            **kwargs,
        }
        self.logger.info(
            f"Command: {command_name} | User: {user_id} | Time: {execution_time_ms}ms | Success: {success}",
            extra={"structured_data": structured_data},
        )

    def log_error_with_context(
        self,
        error_type: str,
        error_message: str,
        component: str,
        stack_trace: Optional[str] = None,
        **kwargs,
    ):
        """Log error with full context for ML analysis."""
        structured_data = {
            "event_type": "error",
            "error_type": error_type,
            "component": component,
            "stack_trace": stack_trace,
            **kwargs,
        }
        self.logger.error(
            f"[{component}] {error_type}: {error_message}",
            extra={"structured_data": structured_data},
        )

    def log_telemetry(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        **tags,
    ):
        """Log performance metric for ML training data."""
        structured_data = {
            "event_type": "telemetry",
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "tags": tags,
        }
        self.logger.debug(
            f"Metric: {metric_name} = {value}{unit} | Tags: {tags}",
            extra={"structured_data": structured_data},
        )

    def log_ml_prediction(
        self,
        model_name: str,
        input_features: Dict[str, Any],
        prediction: Any,
        confidence: float,
        **kwargs,
    ):
        """Log ML prediction for model monitoring."""
        structured_data = {
            "event_type": "ml_prediction",
            "model_name": model_name,
            "input_features": input_features,
            "prediction": str(prediction),
            "confidence": confidence,
            **kwargs,
        }
        self.logger.info(
            f"ML: {model_name} predicted {prediction} (confidence: {confidence:.2f})",
            extra={"structured_data": structured_data},
        )

    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, **kwargs)


def get_logger(name: str) -> SiliconDNALogger:
    """Get a SiliconDNALogger instance."""
    return SiliconDNALogger(name)


class LogBanner:
    """Display startup banner in console."""

    @staticmethod
    def print_banner(name: str, version: str, environment: str = "development"):
        """Print startup banner with system info."""
        env_color = COLORS["green"] if environment == "production" else COLORS["yellow"]

        banner = f"""
{COLORS["bold"]}{COLORS["cyan"]}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      {name} v{version}                                     ║
║      Silicon-Carbon Bridge Architecture                   ║
║                                                           ║
║      Environment: {env_color}{environment.upper()}{COLORS["cyan"]}                                 ║
║      Phase: Database-First Observability                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{COLORS["reset"]}
        """
        print(banner)

    @staticmethod
    def print_status(component: str, status: str, details: str = ""):
        """Print component status during startup."""
        status_color = COLORS["green"] if status == "OK" else COLORS["red"]
        print(
            f"  {COLORS['cyan']}•{COLORS['reset']} {component}: {status_color}{status}{COLORS['reset']} {details}"
        )
