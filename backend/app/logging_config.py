"""Structured logging setup using structlog.

In production we emit JSON logs (machine-parseable, ready for a log
aggregator). In development we emit a colored, human-readable console
renderer. Every log line carries the configured context, so once we add
request IDs / org IDs in later milestones they appear automatically.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import AppEnv, LogLevel


def configure_logging(app_env: AppEnv, log_level: LogLevel) -> None:
    """Configure structlog + stdlib logging for the whole process."""
    level = getattr(logging, log_level.value.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if app_env is AppEnv.production:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
