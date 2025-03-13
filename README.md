# Diagnostics

A comprehensive diagnostics and logging module with performance monitoring capabilities.

## Features

- System metrics collection (memory, CPU, thread count, uptime) [requires psutil]
- Flexible logging system with file and console output
- Function call logging and timing decorators
- Debug function registration and execution
- Log rotation and cleanup functionality

## Installation

```bash
pip install diagnostics
```

For development installation:

```bash
git clone https://github.com/mapledyne/diagnostics.git
cd diagnostics
pip install -e ".[dev]"
```

## Usage

```python
from diagnostics import info, debug, Metrics, log_timing

# Basic logging
info("Application started")
debug(f"Memory usage: {Metrics.memory_usage():.2f} MB")

# Timing function execution
@log_timing
def my_function():
    pass

# System metrics
print(f"CPU Usage: {Metrics.cpu_percent()}%")
print(f"Thread Count: {Metrics.thread_count()}")
print(f"Uptime: {Metrics.uptime_friendly()}")

# Configure logging
from diagnostics import set_log_directory, max_logs
set_log_directory("logs")  # Enable file logging
max_logs(5)  # Keep only the 5 most recent log directories
```

## Development

To set up the development environment:

1. Clone the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest`
4. Format code: `black .`
5. Sort imports: `isort .`
6. Run linter: `flake8`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
