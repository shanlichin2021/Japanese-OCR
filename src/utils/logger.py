"""
Logging Utility - Centralized logging for 代書 (Daisho).

Provides file and console logging with timestamps, log levels,
rotation to prevent unbounded log file growth, system diagnostics,
and performance timing utilities.
"""

from __future__ import annotations
import logging
import os
import sys
import time
import platform
import functools
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Callable, Any
from contextlib import contextmanager


# Log file configuration
LOG_DIR = "logs"
LOG_FILE = "daisho.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # Keep 3 old log files

# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(
    name: str = "代書",
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Set up and configure the application logger.

    Args:
        name: Logger name
        log_level: Minimum level for file logging
        console_level: Minimum level for console logging
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    global _logger

    if _logger is not None:
        return _logger

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation
    if log_to_file:
        try:
            # Create logs directory if it doesn't exist
            if not os.path.exists(LOG_DIR):
                os.makedirs(LOG_DIR)

            log_path = os.path.join(LOG_DIR, LOG_FILE)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=MAX_LOG_SIZE,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    _logger = logger

    # Log startup
    logger.info("=" * 60)
    logger.info(f"MangaReader-OCR Starting - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    return logger


def get_logger() -> logging.Logger:
    """Get the application logger, creating it if necessary."""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


def log_exception(exc: Exception, context: str = "") -> None:
    """
    Log an exception with full traceback.

    Args:
        exc: The exception to log
        context: Additional context about where/why it occurred
    """
    logger = get_logger()
    if context:
        logger.error(f"Exception in {context}: {type(exc).__name__}: {exc}")
    else:
        logger.error(f"Exception: {type(exc).__name__}: {exc}")
    logger.debug("Full traceback:", exc_info=True)


def log_debug(message: str) -> None:
    """Log a debug message."""
    get_logger().debug(message)


def log_info(message: str) -> None:
    """Log an info message."""
    get_logger().info(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    get_logger().warning(message)


def log_error(message: str) -> None:
    """Log an error message."""
    get_logger().error(message)


class LogCapture:
    """
    Context manager to capture stdout/stderr to log file.

    Usage:
        with LogCapture():
            # All print statements will be logged
            print("This goes to log")
    """

    def __init__(self):
        self._stdout = None
        self._stderr = None

    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = _LogWriter(get_logger(), logging.INFO)
        sys.stderr = _LogWriter(get_logger(), logging.ERROR)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        return False


class _LogWriter:
    """File-like object that writes to a logger."""

    def __init__(self, logger: logging.Logger, level: int):
        self._logger = logger
        self._level = level
        self._buffer = ""

    def write(self, message: str) -> None:
        if message and message.strip():
            self._logger.log(self._level, message.rstrip())

    def flush(self) -> None:
        pass


# =============================================================================
# System Diagnostics
# =============================================================================

def log_system_info() -> None:
    """Log comprehensive system information for debugging."""
    logger = get_logger()

    logger.info("-" * 60)
    logger.info("SYSTEM DIAGNOSTICS")
    logger.info("-" * 60)

    # Platform info
    logger.info(f"Platform: {platform.system()} {platform.release()}")
    logger.info(f"Platform Version: {platform.version()}")
    logger.info(f"Machine: {platform.machine()}")
    logger.info(f"Processor: {platform.processor()}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Python Executable: {sys.executable}")

    # Memory info (if psutil available)
    try:
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"RAM: {mem.total / (1024**3):.1f} GB total, {mem.available / (1024**3):.1f} GB available")
    except ImportError:
        logger.debug("psutil not available for memory info")

    # GPU info
    _log_gpu_info(logger)

    # Key package versions
    _log_package_versions(logger)

    logger.info("-" * 60)


def _log_gpu_info(logger: logging.Logger) -> None:
    """Log GPU availability and information."""
    # PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"PyTorch CUDA: Available - {torch.cuda.get_device_name(0)}")
            logger.info(f"PyTorch CUDA Version: {torch.version.cuda}")
            mem_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"GPU Memory: {mem_total:.1f} GB")
        else:
            logger.info("PyTorch CUDA: Not available (CPU mode)")
    except ImportError:
        logger.info("PyTorch: Not installed")
    except Exception as e:
        logger.warning(f"PyTorch GPU check failed: {e}")

    # PaddlePaddle
    try:
        import paddle
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                logger.info(f"PaddlePaddle CUDA: Available, {gpu_count} GPU(s)")
            else:
                logger.info("PaddlePaddle CUDA: Compiled but no GPU found")
        else:
            logger.info("PaddlePaddle: CPU version")
    except ImportError:
        logger.info("PaddlePaddle: Not installed")
    except Exception as e:
        logger.warning(f"PaddlePaddle GPU check failed: {e}")


def _log_package_versions(logger: logging.Logger) -> None:
    """Log versions of key packages."""
    packages = [
        "PyQt6",
        "manga_ocr",
        "paddleocr",
        "paddlepaddle",
        "torch",
        "opencv-python-headless",
        "Pillow",
        "numpy",
    ]

    logger.info("Package Versions:")
    for pkg in packages:
        try:
            # Handle package name variations
            import_name = pkg.replace("-", "_").replace("opencv_python_headless", "cv2")
            if import_name == "cv2":
                import cv2
                version = cv2.__version__
            elif import_name == "Pillow":
                from PIL import __version__ as version
            else:
                import importlib
                mod = importlib.import_module(import_name)
                version = getattr(mod, "__version__", "unknown")
            logger.info(f"  {pkg}: {version}")
        except ImportError:
            logger.debug(f"  {pkg}: Not installed")
        except Exception as e:
            logger.debug(f"  {pkg}: Error getting version - {e}")


# =============================================================================
# Performance Timing
# =============================================================================

@contextmanager
def log_timing(operation: str, level: int = logging.DEBUG):
    """
    Context manager to log the duration of an operation.

    Usage:
        with log_timing("OCR inference"):
            result = ocr_engine.perform_ocr(image)
    """
    logger = get_logger()
    start = time.perf_counter()
    logger.log(level, f"Starting: {operation}")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        if elapsed < 1:
            logger.log(level, f"Completed: {operation} in {elapsed*1000:.1f}ms")
        else:
            logger.log(level, f"Completed: {operation} in {elapsed:.2f}s")


def timed(func: Callable) -> Callable:
    """
    Decorator to log function execution time.

    Usage:
        @timed
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            log_debug(f"{func.__name__} completed in {elapsed*1000:.1f}ms")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            log_error(f"{func.__name__} failed after {elapsed*1000:.1f}ms: {e}")
            raise
    return wrapper


# =============================================================================
# Log Analysis Utilities
# =============================================================================

def get_recent_errors(count: int = 10) -> list[str]:
    """
    Read and return recent ERROR level entries from the log file.

    Args:
        count: Maximum number of error entries to return

    Returns:
        List of recent error log lines
    """
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    if not os.path.exists(log_path):
        return []

    errors = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '| ERROR' in line or '| CRITICAL' in line:
                    errors.append(line.strip())
        return errors[-count:]
    except Exception:
        return []


def get_recent_warnings(count: int = 10) -> list[str]:
    """
    Read and return recent WARNING level entries from the log file.

    Args:
        count: Maximum number of warning entries to return

    Returns:
        List of recent warning log lines
    """
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    if not os.path.exists(log_path):
        return []

    warnings = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '| WARNING' in line:
                    warnings.append(line.strip())
        return warnings[-count:]
    except Exception:
        return []


def check_log_health() -> dict:
    """
    Analyze log file and return health summary.

    Returns:
        Dictionary with log health metrics
    """
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    result = {
        "log_exists": False,
        "log_size_kb": 0,
        "error_count": 0,
        "warning_count": 0,
        "last_entry": None,
        "recent_errors": [],
    }

    if not os.path.exists(log_path):
        return result

    result["log_exists"] = True
    result["log_size_kb"] = os.path.getsize(log_path) / 1024

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            if '| ERROR' in line or '| CRITICAL' in line:
                result["error_count"] += 1
                result["recent_errors"].append(line.strip())
            elif '| WARNING' in line:
                result["warning_count"] += 1

        # Keep only last 5 errors
        result["recent_errors"] = result["recent_errors"][-5:]

        # Get last entry
        if lines:
            result["last_entry"] = lines[-1].strip()

    except Exception as e:
        result["read_error"] = str(e)

    return result


def print_log_health() -> None:
    """Print a formatted log health report to console and log."""
    health = check_log_health()

    report = [
        "",
        "=" * 50,
        "LOG HEALTH REPORT",
        "=" * 50,
        f"Log file exists: {health['log_exists']}",
        f"Log size: {health['log_size_kb']:.1f} KB",
        f"Total errors: {health['error_count']}",
        f"Total warnings: {health['warning_count']}",
    ]

    if health.get("recent_errors"):
        report.append("")
        report.append("Recent Errors:")
        for err in health["recent_errors"]:
            # Truncate long lines
            if len(err) > 100:
                err = err[:97] + "..."
            report.append(f"  {err}")

    if health.get("last_entry"):
        report.append("")
        report.append(f"Last log entry: {health['last_entry'][:80]}...")

    report.append("=" * 50)

    for line in report:
        print(line)
        log_info(line) if line.strip() else None
