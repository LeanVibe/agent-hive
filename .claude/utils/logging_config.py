# .claude/utils/logging_config.py
"""Structured logging configuration for LeanVibe orchestration system."""

import json
import logging
import logging.handlers
import sys
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.config_loader import get_config

# Context variables for correlation tracking
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')
task_id_var: ContextVar[str] = ContextVar('task_id', default='')
agent_id_var: ContextVar[str] = ContextVar('agent_id', default='')


class CorrelationFilter(logging.Filter):
    """Add correlation ID and context to log records."""

    def filter(self, record):
        record.correlation_id = correlation_id_var.get('')
        record.task_id = task_id_var.get('')
        record.agent_id = agent_id_var.get('')
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'correlation_id': getattr(record, 'correlation_id', ''),
            'task_id': getattr(record, 'task_id', ''),
            'agent_id': getattr(record, 'agent_id', ''),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'correlation_id', 'task_id',
                          'agent_id']:
                log_entry[key] = value

        return json.dumps(log_entry)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    def format(self, record):
        correlation_id = getattr(record, 'correlation_id', '')
        task_id = getattr(record, 'task_id', '')
        agent_id = getattr(record, 'agent_id', '')

        # Build context string
        context_parts = []
        if correlation_id:
            context_parts.append(f"corr={correlation_id[:8]}")
        if task_id:
            context_parts.append(f"task={task_id}")
        if agent_id:
            context_parts.append(f"agent={agent_id}")

        context_str = f"[{', '.join(context_parts)}]" if context_parts else ""

        # Format timestamp
        timestamp = datetime.fromtimestamp(
    record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Build log line
        log_line = f"{timestamp} {
    record.levelname:8} {
        record.name:20} {
            context_str:30} {
                record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"

        return log_line


def setup_logging(
    log_level: str = None,
    log_file: Optional[str] = None,
    json_format: bool = False,
    console_output: bool = True
) -> None:
    """Set up structured logging for the application.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        json_format: Use JSON formatting for file output
        console_output: Enable console output
    """
    config = get_config()

    # Get configuration
    if log_level is None:
        log_level = config.get('system.log_level', 'INFO')

    # Create logs directory
    log_dir = Path('.claude/logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Add correlation filter
    correlation_filter = CorrelationFilter()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(HumanReadableFormatter())
        console_handler.addFilter(correlation_filter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file is None:
        log_file = log_dir / 'leanvibe.log'

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))

    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(HumanReadableFormatter())

    file_handler.addFilter(correlation_filter)
    root_logger.addHandler(file_handler)

    # Error file handler (only errors and above)
    error_file = log_dir / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(correlation_filter)
    root_logger.addHandler(error_handler)

    # Set specific logger levels
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger('leanvibe.startup')
    logger.info(f"Logging initialized with level {log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get logger with consistent naming.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(f'leanvibe.{name}')


def set_correlation_id(correlation_id: str = None) -> str:
    """Set correlation ID for request tracking.

    Args:
        correlation_id: Correlation ID or None to generate new one

    Returns:
        Correlation ID
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    correlation_id_var.set(correlation_id)
    return correlation_id


def set_task_context(task_id: str, agent_id: str = None):
    """Set task context for logging.

    Args:
        task_id: Task ID
        agent_id: Agent ID (optional)
    """
    task_id_var.set(task_id)
    if agent_id:
        agent_id_var.set(agent_id)


def clear_context():
    """Clear logging context."""
    correlation_id_var.set('')
    task_id_var.set('')
    agent_id_var.set('')


def log_performance(operation: str, duration: float,
                    extra_data: Dict[str, Any] = None):
    """Log performance metrics.

    Args:
        operation: Operation name
        duration: Duration in seconds
        extra_data: Additional data to log
    """
    logger = get_logger('performance')

    perf_data = {
        'operation': operation,
        'duration_seconds': duration,
        'duration_ms': duration * 1000,
    }

    if extra_data:
        perf_data.update(extra_data)

    logger.info(
    f"Performance: {operation} took {
        duration:.3f}s",
         extra=perf_data)


def log_error(error: Exception, context: str = None,
              extra_data: Dict[str, Any] = None):
    """Log error with structured information.

    Args:
        error: Exception object
        context: Context description
        extra_data: Additional data to log
    """
    logger = get_logger('errors')

    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context or 'Unknown',
    }

    if extra_data:
        error_data.update(extra_data)

    logger.error(
    f"Error in {context}: {error}",
    exc_info=True,
     extra=error_data)


# Context manager for correlation tracking
class CorrelationContext:
    """Context manager for correlation tracking."""

    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id
        self.old_correlation_id = None

    def __enter__(self):
        self.old_correlation_id = correlation_id_var.get('')
        self.correlation_id = set_correlation_id(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_var.set(self.old_correlation_id)


# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()
