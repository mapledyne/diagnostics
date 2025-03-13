#!/usr/bin/env python3
"""Network diagnostics command-line interface.

This module provides a CLI for the network diagnostics functionality.
Run with: python -m diagnostics.network [command] [options]
"""

import argparse
import json
import sys
from typing import Optional

from .network import (
    NetworkMetrics,
    ConnectionMonitor,
    LatencyMonitor,
    DNSMonitor,
    SSLCertMonitor,
)


def format_json(data: dict) -> str:
    """Format data as pretty JSON."""
    return json.dumps(data, indent=2)


def main() -> Optional[int]:
    """Main entry point for the network diagnostics CLI."""
    parser = argparse.ArgumentParser(
        description="Network diagnostics tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Network metrics command
    metrics_parser = subparsers.add_parser(
        "metrics", help="Show network interface metrics"
    )
    metrics_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Connections command
    conn_parser = subparsers.add_parser(
        "connections", help="Show network connections"
    )
    conn_parser.add_argument(
        "--status", help="Filter connections by status"
    )
    conn_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # Latency command
    latency_parser = subparsers.add_parser(
        "latency", help="Measure network latency"
    )
    latency_parser.add_argument("host", help="Host to measure latency to")
    latency_parser.add_argument(
        "--port", type=int, default=80, help="Port to connect to (default: 80)"
    )
    latency_parser.add_argument(
        "--count", type=int, default=5, help="Number of measurements (default: 5)"
    )
    latency_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # DNS command
    dns_parser = subparsers.add_parser(
        "dns", help="DNS resolution and cache info"
    )
    dns_parser.add_argument("hostname", help="Hostname to resolve")
    dns_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    # SSL command
    ssl_parser = subparsers.add_parser(
        "ssl", help="SSL/TLS certificate information"
    )
    ssl_parser.add_argument("hostname", help="Host to check certificate for")
    ssl_parser.add_argument(
        "--port", type=int, default=443, help="Port to connect to (default: 443)"
    )
    ssl_parser.add_argument(
        "--json", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "metrics":
            metrics = NetworkMetrics()
            data = {
                "interfaces": metrics.get_interface_stats(),
                "connections": metrics.get_connections(),
            }
            if args.json:
                print(format_json(data))
            else:
                print("Network Interfaces:")
                for interface, stats in data["interfaces"].items():
                    print(f"\n{interface}:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                print("\nActive Connections:")
                for conn in data["connections"]:
                    print(f"\n  {conn}")

        elif args.command == "connections":
            monitor = ConnectionMonitor()
            if args.status:
                data = monitor.get_connections_by_status(args.status)
            else:
                data = monitor.get_connection_summary()
            if args.json:
                print(format_json(data))
            else:
                if args.status:
                    print(f"\nConnections with status '{args.status}':")
                    for conn in data:
                        print(f"  {conn}")
                else:
                    print("\nConnection Summary:")
                    for status, count in data.items():
                        print(f"  {status}: {count}")

        elif args.command == "latency":
            monitor = LatencyMonitor()
            latencies = []
            for _ in range(args.count):
                latency = monitor.measure_latency(args.host, args.port)
                if latency is not None:
                    latencies.append(latency)
                else:
                    print(
                        f"Failed to measure latency to {args.host}",
                        file=sys.stderr
                    )
                    return 1

            data = {
                "host": args.host,
                "port": args.port,
                "measurements": latencies,
                "stats": {
                    "min": min(latencies),
                    "max": max(latencies),
                    "avg": sum(latencies) / len(latencies),
                }
            }
            if args.json:
                print(format_json(data))
            else:
                print(f"\nLatency to {args.host}:")
                print(f"  Min: {data['stats']['min']:.3f}s")
                print(f"  Max: {data['stats']['max']:.3f}s")
                print(f"  Avg: {data['stats']['avg']:.3f}s")
                print("\nMeasurements:")
                for i, latency in enumerate(data["measurements"], 1):
                    print(f"  {i}: {latency:.3f}s")

        elif args.command == "dns":
            monitor = DNSMonitor()
            ips = monitor.resolve(args.hostname)
            if ips is None:
                print(f"Failed to resolve {args.hostname}", file=sys.stderr)
                return 1

            data = {
                "hostname": args.hostname,
                "ip_addresses": ips,
                "cache_stats": monitor.get_cache_stats(),
            }
            if args.json:
                print(format_json(data))
            else:
                print(f"\nDNS Resolution for {args.hostname}:")
                print("IP Addresses:")
                for ip in data["ip_addresses"]:
                    print(f"  {ip}")
                print("\nCache Statistics:")
                for key, value in data["cache_stats"].items():
                    print(f"  {key}: {value}")

        elif args.command == "ssl":
            monitor = SSLCertMonitor()
            cert_info = monitor.check_certificate(args.hostname, args.port)
            if cert_info is None:
                print(
                    f"Failed to check certificate for {args.hostname}",
                    file=sys.stderr
                )
                return 1

            data = {
                "hostname": args.hostname,
                "port": args.port,
                "certificate": cert_info,
                "cache_stats": monitor.get_cache_stats(),
            }
            if args.json:
                print(format_json(data))
            else:
                print(f"\nSSL Certificate for {args.hostname}:")
                print("\nSubject:")
                for key, value in data["certificate"]["subject"].items():
                    print(f"  {key}: {value}")
                print("\nIssuer:")
                for key, value in data["certificate"]["issuer"].items():
                    print(f"  {key}: {value}")
                print("\nValidity:")
                print(f"  Not Before: {data['certificate']['not_before']}")
                print(f"  Not After: {data['certificate']['not_after']}")
                print(
                    f"  Serial Number: {data['certificate']['serial_number']}"
                )
                print(f"  Version: {data['certificate']['version']}")
                print("\nCache Statistics:")
                for key, value in data["cache_stats"].items():
                    print(f"  {key}: {value}")

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 