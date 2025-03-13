#!/usr/bin/env python3
"""Diagnostics command-line interface.

This module provides a CLI for all diagnostics functionality.
Run with: python -m diagnostics [command] [options]
"""

import argparse
import json
import sys
from typing import Optional

from . import Metrics
from .network import (
    NetworkMetrics,
    ConnectionMonitor,
    LatencyMonitor,
    DNSMonitor,
    SSLCertMonitor,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Diagnostics tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # System metrics command
    metrics_parser = subparsers.add_parser(
        "metrics", help="Show system metrics"
    )
    metrics_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Network subcommands
    network_parser = subparsers.add_parser(
        "network", help="Network diagnostics"
    )
    network_subparsers = network_parser.add_subparsers(
        dest="network_command", help="Available network commands"
    )

    # Network metrics
    network_metrics_parser = network_subparsers.add_parser(
        "metrics", help="Show network interface metrics"
    )
    network_metrics_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Network connections
    network_conn_parser = network_subparsers.add_parser(
        "connections", help="Show network connections"
    )
    network_conn_parser.add_argument(
        "--status", help="Filter connections by status"
    )
    network_conn_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Network latency
    network_latency_parser = network_subparsers.add_parser(
        "latency", help="Measure network latency"
    )
    network_latency_parser.add_argument("host", help="Host to measure latency to")
    network_latency_parser.add_argument(
        "--port", type=int, default=80, help="Port to connect to (default: 80)"
    )
    network_latency_parser.add_argument(
        "--count", type=int, default=5, help="Number of measurements (default: 5)"
    )
    network_latency_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Network DNS
    network_dns_parser = network_subparsers.add_parser(
        "dns", help="DNS resolution and cache info"
    )
    network_dns_parser.add_argument("hostname", help="Hostname to resolve")
    network_dns_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Network SSL
    network_ssl_parser = network_subparsers.add_parser(
        "ssl", help="SSL/TLS certificate information"
    )
    network_ssl_parser.add_argument("hostname", help="Host to check certificate for")
    network_ssl_parser.add_argument(
        "--port", type=int, default=443, help="Port to connect to (default: 443)"
    )
    network_ssl_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    return parser


def main() -> Optional[int]:
    """Main entry point for the diagnostics CLI."""
    parser = create_parser()
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2:  # Invalid command
            parser.print_help()
        return e.code

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "metrics":
            data = {
                "memory_usage": Metrics.memory_usage(),
                "cpu_percent": Metrics.cpu_percent(),
                "thread_count": Metrics.thread_count(),
                "app uptime (should be close to 0 if run from CLI)": Metrics.uptime(),
                "app uptime_friendly": Metrics.uptime_friendly(),
            }
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                print("\nSystem Metrics:")
                for key, value in data.items():
                    print(f"  {key}: {value}")

        elif args.command == "network":
            if not args.network_command:
                network_parser = next(
                    subparser for subparser in parser._subparsers._actions
                    if subparser.dest == "command"
                ).choices["network"]
                network_parser.print_help()
                return 0

            # Import network module's main function
            from .network.__main__ import main as network_main
            # Pass the remaining arguments to the network module
            sys.argv = [sys.argv[0]] + sys.argv[2:]
            return network_main()

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 