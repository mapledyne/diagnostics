"""A comprehensive diagnostics and logging module.

This module provides a robust logging and diagnostics system with performance monitoring capabilities.
It offers a flexible and extensible way to track application behavior, system metrics, and debug information.

Key features:
- System metrics collection (memory, CPU, thread count, uptime) [requires psutil]
- Flexible logging system with file and console output
- Function call logging and timing decorators
- Debug function registration and execution
- Log rotation and cleanup functionality

The logging system supports both file and console output with customizable log levels and formats.
All logs include detailed caller information (module, function, line number) for better traceability.

Example usage:
    >>> from diagnostics import info, debug, Metrics
    >>> info("Application started")
    >>> debug(f"Memory usage: {Metrics.memory_usage():.2f} MB")
    >>> @log_timing
    >>> def my_function():
    ...     pass
"""
# Standard library imports
import logging
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Callable, Optional, List

# Third-party imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    warnings.warn("psutil not installed. System metrics collection will be disabled.")


class Metrics:
    @staticmethod
    def memory_usage() -> float:
        """Get current memory usage in MB. Requires psutil to be installed."""
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is not installed. System metrics are unavailable.")
        return psutil.Process().memory_info().rss / 1024 / 1024

    @staticmethod 
    def cpu_percent() -> float:
        """Get current CPU usage percentage. Requires psutil to be installed."""
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is not installed. System metrics are unavailable.")
        return psutil.cpu_percent()

    @staticmethod
    def thread_count() -> int:
        """Get current thread count. Requires psutil to be installed."""
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is not installed. System metrics are unavailable.")
        return len(psutil.Process().threads())
        
    @staticmethod
    def uptime() -> float:
        """Get process uptime in seconds. Requires psutil to be installed."""
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is not installed. System metrics are unavailable.")
        return time.time() - psutil.Process().create_time()

    @staticmethod
    def uptime_friendly() -> str:
        """Get process uptime in a human-readable format. Requires psutil to be installed."""
        if not PSUTIL_AVAILABLE:
            raise RuntimeError("psutil is not installed. System metrics are unavailable.")
        seconds = Metrics.uptime()
        return str(timedelta(seconds=int(seconds)))


def running_under_unittest() -> bool:
    """Check if the code is being run under a unittest."""
    return 'unittest' in sys.modules


def current_log_dir() -> str:
    return f"{_log_directory}\\{timestamp}"


def log_function_call(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        debug(f"Calling function: {func.__name__}")
        debug(f"Arguments: {args}")
        debug(f"Keyword arguments: {kwargs}")
        try:
            result = func(*args, **kwargs)
            debug(f"Function {func.__name__} returned: {result}")
            return result
        except Exception as e:
            error(f"Function {func.__name__} raised an exception: {e}")
            raise
    return wrapper


def log_timing(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        info(f"Function {func.__name__} took {elapsed_time:.2f} seconds")
        return result
    return wrapper


def deprecated(message: str = "This function is deprecated.") -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(f"{func.__name__}: {message}", DeprecationWarning, stacklevel=2)
            warning(f"DEPRECATED: {func.__name__}: {message}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log(level, message):
    caller_info = logger.findCaller(stack_info=False, stacklevel=3)
    full_path = caller_info[0]
    project_root = os.getcwd()  # Assuming the current working directory is the project root
    relative_path = os.path.relpath(full_path, start=project_root)

    extra = {
        "caller_module": relative_path.replace("\\", "/"),
        "caller_func": caller_info[2],
        "caller_lineno": caller_info[1],
    }
    logger._log(level, message, args=(), extra=extra)


def debug(message):
    log(logging.DEBUG, message)


def info(message):
    log(logging.INFO, message)


def warning(message):
    log(logging.WARNING, message)


def error(message):
    log(logging.ERROR, message)


def critical(message):
    log(logging.CRITICAL, message)


def max_logs(val: int) -> None:
    global _max_logs
    if val < 1:
        _max_logs = -1
        return

    _max_logs = val
    cleanup_logs()


def log_level(val: int) -> None:
    """
    Set the logging level for the logger and all its handlers.

    Args:
        val (int): Logging level to set.
    """
    logger.setLevel(val)
    for handler in logger.handlers:
        handler.setLevel(val)


def get_log_directory() -> Optional[str]:
    return _log_directory


def set_log_directory(directory: Optional[str]) -> None:
    global _file_handler, _log_directory

    if directory is None:
        if _file_handler:
            logging.getLogger().removeHandler(_file_handler)
            _file_handler.close()
            _file_handler = None
            info("File logging disabled.")
        _log_directory = None
    else:
        if not os.path.exists(directory):
            os.makedirs(directory)

        _log_directory = directory
        os.makedirs(current_log_dir(), exist_ok=True)

        log_file_path = os.path.join(current_log_dir(), "debug.log")
        if _file_handler:
            logger.removeHandler(_file_handler)
            _file_handler.close()

        _file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        _file_handler.setFormatter(formatter)
        _file_handler.setLevel(logger.level)
        logger.addHandler(_file_handler)

        info(f"File logging enabled. Logs are saved to: {log_file_path}")


def register_debug_function(func: Callable) -> None:
    if callable(func):
        debug_functions.append(func)
        debug(f"Registered exit logging function: {func.__name__}")
    else:
        warning(f"Attempted to register a non-callable object: {func}")


def run_debug_functions() -> None:
    """ Execute all registered debug functions and log their output. """
    info("Running registered exit logging functions...")
    for func in debug_functions:
        if "." in func.__qualname__:
            log_file_name = func.__qualname__.split(".")[0]
        else:
            log_file_name = func.__name__

        try:
            output = func()

            if output:
                log_file = current_log_dir() + f"\\{log_file_name}.log"
                file_exists_and_non_empty = os.path.exists(log_file) and os.path.getsize(log_file) > 0

                with open(log_file, "a", encoding="utf-8") as f:
                    if file_exists_and_non_empty:
                        f.write("\n\n" + "*" * 80 + "\n\n\n")
                    f.write(output + "\n")
                info(f"Appended output for {func.__qualname__} to {log_file}")
        except Exception as e:
            error(f"Error running debug function {func.__qualname__}: {e}")


def cleanup_logs() -> None:
    """ Remove old log directories, keeping only the latest as specified by max_logs. """
    if _max_logs < 1:
        return
    log_dirs = sorted(
        [d for d in Path(_log_directory).iterdir() if d.is_dir()],  # type: ignore
        key=lambda d: d.name
    )
    keep_count = len(log_dirs) - _max_logs
    if keep_count > 0:
        excess_dirs = log_dirs[:keep_count]
        for old_dir in excess_dirs:
            for item in old_dir.iterdir():
                item.unlink()
            old_dir.rmdir()
            info(f"Removed old log directory: {old_dir}")


# Global variables
timestamp: str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
_max_logs: int = -1
_log_directory: Optional[str] = None
_file_handler: Optional[logging.FileHandler] = None
debug_visuals: bool = False
debug_functions: List[Callable] = []

# Configure a dedicated logger for DebugManager
logger: logging.Logger = logging.getLogger("DebugManager")
logger.setLevel(logging.ERROR)
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(caller_module)s.%(caller_func)s:%(caller_lineno)d - %(message)s"
)

if not running_under_unittest():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
logger.propagate = False
