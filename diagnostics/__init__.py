"""A diagnostics and logging module.

This module provides logging and diagnostics system with performance monitoring capabilities.
It offers a flexible and extensible way to track application behavior, system metrics, and debug information.

Key features:
- System metrics collection (memory, CPU, thread count, uptime) [requires psutil]
- Flexible logging system with file and console output
- Function call logging and timing decorators
- Debug function registration and execution
- Log rotation and cleanup functionality
"""

from .diagnostics import (
    Metrics,
    debug,
    info,
    warning,
    error,
    critical,
    log_timing,
    log_function_call,
    deprecated,
    register_debug_function,
    run_debug_functions,
    set_log_directory,
    get_log_directory,
    max_logs,
    log_level,
    cleanup_logs,
)

__version__ = "0.1.0"
__all__ = [
    "Metrics",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "log_timing",
    "log_function_call",
    "deprecated",
    "register_debug_function",
    "run_debug_functions",
    "set_log_directory",
    "get_log_directory",
    "max_logs",
    "log_level",
    "cleanup_logs",
] 