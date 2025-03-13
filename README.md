# Diagnostics

A comprehensive diagnostics and logging module with performance monitoring capabilities.

## Features

- System metrics collection (memory, CPU, thread count, uptime) [requires psutil]
- Network diagnostics including:
  - Network interface statistics
  - Connection monitoring
  - Latency measurements
  - DNS resolution and caching
  - SSL/TLS certificate validation
- Flexible logging system with file and console output
- Function call logging and timing decorators
- Debug function registration and execution
- Log rotation and cleanup functionality

## Installation

Since this package is not on PyPI, install directly from the repository:

```bash
git clone https://github.com/mapledyne/diagnostics.git
cd diagnostics
```

## Usage

```python
from diagnostics import info, debug, Metrics, log_timing
from diagnostics.network import (
    NetworkMetrics,
    ConnectionMonitor,
    LatencyMonitor,
    DNSMonitor,
    SSLCertMonitor,
)

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

# Network diagnostics
network_metrics = NetworkMetrics()
print(f"Network Interfaces: {network_metrics.get_interface_stats()}")
print(f"Active Connections: {network_metrics.get_connections()}")

# Latency monitoring
latency_monitor = LatencyMonitor()
latency_monitor.track_latency('google.com')
print(f"Latency Stats: {latency_monitor.get_latency_stats('google.com')}")

# DNS resolution
dns_monitor = DNSMonitor()
ips = dns_monitor.resolve('google.com')
print(f"Resolved IPs: {ips}")

# SSL certificate checking
ssl_monitor = SSLCertMonitor()
cert_info = ssl_monitor.check_certificate('google.com')
print(f"Certificate Info: {cert_info}")

# Configure logging
from diagnostics import set_log_directory, max_logs
set_log_directory("logs")  # Enable file logging
max_logs(5)  # Keep only the 5 most recent log directories
```

## Command Line Interface

The package includes a CLI for network diagnostics:

```bash
# Show network metrics
python -m diagnostics network metrics

# Show network connections
python -m diagnostics network connections

# Measure latency
python -m diagnostics network latency google.com

# DNS resolution
python -m diagnostics network dns google.com

# SSL certificate check
python -m diagnostics network ssl google.com
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
