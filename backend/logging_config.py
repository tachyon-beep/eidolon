"""
Structured logging configuration for MONAD

Provides structured, searchable logging with context binding and correlation.
Replaces basic print() statements with production-grade logging.
"""
import structlog
import logging
import sys
from typing import Optional


def configure_logging(log_level: str = "INFO", json_logs: bool = False):
    """
    Configure structured logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: If True, output JSON format (for production)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )

    # Processors for all log entries
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add JSON rendering for production, pretty printing for development
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None):
    """
    Get a configured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    return structlog.get_logger(name)


def bind_context(**kwargs):
    """
    Bind context variables for all subsequent logs in this async context

    Example:
        bind_context(session_id="abc123", user_id="user456")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys):
    """
    Remove specific context variables

    Example:
        unbind_context("session_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context():
    """Clear all context variables"""
    structlog.contextvars.clear_contextvars()
