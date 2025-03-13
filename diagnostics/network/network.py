"""Network diagnostics implementation.

This module provides various network diagnostic tools and metrics collection.
"""

import socket
import ssl
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import psutil
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from .. import debug, error, info, warning


class NetworkMetrics:
    """Collect and provide network interface statistics."""

    @staticmethod
    def get_interface_stats() -> Dict[str, Dict[str, Union[int, float]]]:
        """Get statistics for all network interfaces.
        
        Returns:
            Dict mapping interface names to their statistics including:
            - bytes_sent: Total bytes sent
            - bytes_recv: Total bytes received
            - packets_sent: Total packets sent
            - packets_recv: Total packets received
            - errin: Total errors received
            - errout: Total errors sent
            - dropin: Total packets dropped on receive
            - dropout: Total packets dropped on send
        """
        stats = {}
        for interface, addrs in psutil.net_if_stats().items():
            try:
                stats[interface] = {
                    "bytes_sent": addrs.bytes_sent,
                    "bytes_recv": addrs.bytes_recv,
                    "packets_sent": addrs.packets_sent,
                    "packets_recv": addrs.packets_recv,
                    "errin": addrs.errin,
                    "errout": addrs.errout,
                    "dropin": addrs.dropin,
                    "dropout": addrs.dropout,
                }
            except AttributeError:
                # Some interfaces might not have all stats
                stats[interface] = {
                    "bytes_sent": 0,
                    "bytes_recv": 0,
                    "packets_sent": 0,
                    "packets_recv": 0,
                    "errin": 0,
                    "errout": 0,
                    "dropin": 0,
                    "dropout": 0,
                }
        return stats

    @staticmethod
    def get_connections() -> List[Dict[str, Union[str, int]]]:
        """Get all network connections.
        
        Returns:
            List of dictionaries containing connection information:
            - fd: File descriptor
            - family: Address family (IPv4/IPv6)
            - type: Socket type
            - local_addr: Local address and port
            - remote_addr: Remote address and port
            - status: Connection status
            - pid: Process ID
        """
        connections = []
        for conn in psutil.net_connections():
            connections.append({
                "fd": conn.fd,
                "family": conn.family,
                "type": conn.type,
                "local_addr": conn.laddr,
                "remote_addr": conn.raddr,
                "status": conn.status,
                "pid": conn.pid,
            })
        return connections


class ConnectionMonitor:
    """Monitor network connections and their states."""

    def __init__(self):
        self._connections: Dict[str, List[Dict]] = {}
        self._last_check = 0
        self._check_interval = 1.0  # seconds

    def update(self) -> None:
        """Update connection statistics."""
        current_time = time.time()
        if current_time - self._last_check < self._check_interval:
            return

        self._connections = {}
        for conn in psutil.net_connections():
            status = conn.status
            if status not in self._connections:
                self._connections[status] = []
            self._connections[status].append({
                "local": conn.laddr,
                "remote": conn.raddr,
                "pid": conn.pid,
            })
        self._last_check = current_time

    def get_connection_summary(self) -> Dict[str, int]:
        """Get summary of connections by status.
        
        Returns:
            Dict mapping connection status to count
        """
        self.update()
        return {status: len(conns) for status, conns in self._connections.items()}

    def get_connections_by_status(self, status: str) -> List[Dict]:
        """Get all connections with a specific status.
        
        Args:
            status: Connection status to filter by
            
        Returns:
            List of connection details
        """
        self.update()
        return self._connections.get(status, [])


class LatencyMonitor:
    """Monitor network latency to specified hosts."""

    def __init__(self):
        self._latencies: Dict[str, List[float]] = {}
        self._last_check = 0
        self._check_interval = 5.0  # seconds

    def measure_latency(self, host: str, port: int = 80, timeout: float = 1.0) -> Optional[float]:
        """Measure latency to a host.
        
        Args:
            host: Host to measure latency to
            port: Port to connect to
            timeout: Connection timeout in seconds
            
        Returns:
            Latency in seconds or None if measurement failed
        """
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            latency = time.time() - start_time
            sock.close()
            return latency
        except (socket.timeout, socket.error) as e:
            warning(f"Failed to measure latency to {host}: {e}")
            return None

    def track_latency(self, host: str, port: int = 80) -> None:
        """Track latency to a host over time.
        
        Args:
            host: Host to track latency for
            port: Port to connect to
        """
        current_time = time.time()
        debug(f"track_latency called for {host} at time {current_time}")
        debug(f"Last check was at {self._last_check}")
        debug(f"Check interval is {self._check_interval}")
        
        if current_time - self._last_check < self._check_interval:
            debug(f"Skipping measurement - within check interval")
            return

        latency = self.measure_latency(host, port)
        debug(f"Measured latency: {latency}")
        
        if latency is not None:
            if host not in self._latencies:
                debug(f"Creating new entry for {host}")
                self._latencies[host] = []
            self._latencies[host].append(latency)
            debug(f"Added latency {latency} for {host}")
            # Keep only last 100 measurements
            self._latencies[host] = self._latencies[host][-100:]
        else:
            debug(f"No latency measurement recorded for {host}")
        
        self._last_check = current_time
        debug(f"Updated last check time to {self._last_check}")

    def get_latency_stats(self, host: str) -> Optional[Dict[str, float]]:
        """Get latency statistics for a host.
        
        Args:
            host: Host to get statistics for
            
        Returns:
            Dict containing min, max, avg latency or None if no data
        """
        if host not in self._latencies or not self._latencies[host]:
            return None

        latencies = self._latencies[host]
        return {
            "min": min(latencies),
            "max": max(latencies),
            "avg": sum(latencies) / len(latencies),
        }


class DNSMonitor:
    """Monitor DNS resolution and caching."""

    def __init__(self):
        self._cache: Dict[str, Tuple[List[str], float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def resolve(self, hostname: str) -> Optional[List[str]]:
        """Resolve a hostname to IP addresses.
        
        Args:
            hostname: Hostname to resolve
            
        Returns:
            List of IP addresses or None if resolution failed
        """
        try:
            # Check cache first
            if hostname in self._cache:
                ips, timestamp = self._cache[hostname]
                if time.time() - timestamp < self._cache_ttl:
                    return ips

            # Perform DNS lookup
            ips = socket.gethostbyname_ex(hostname)[2]
            self._cache[hostname] = (ips, time.time())
            return ips
        except socket.gaierror as e:
            error(f"DNS resolution failed for {hostname}: {e}")
            return None

    def get_cache_stats(self) -> Dict[str, int]:
        """Get DNS cache statistics.
        
        Returns:
            Dict containing cache size and hit/miss counts
        """
        return {
            "size": len(self._cache),
            "entries": sum(1 for _, (_, timestamp) in self._cache.items()
                          if time.time() - timestamp < self._cache_ttl),
        }


class SSLCertMonitor:
    """Monitor SSL/TLS certificates."""

    def __init__(self):
        self._cache: Dict[str, Tuple[x509.Certificate, float]] = {}
        self._cache_ttl = 3600  # 1 hour

    def check_certificate(self, hostname: str, port: int = 443) -> Optional[Dict]:
        """Check SSL/TLS certificate for a host.
        
        Args:
            hostname: Host to check certificate for
            port: Port to connect to
            
        Returns:
            Dict containing certificate information or None if check failed
        """
        try:
            # Check cache first
            if hostname in self._cache:
                cert, timestamp = self._cache[hostname]
                if time.time() - timestamp < self._cache_ttl:
                    return self._get_cert_info(cert)

            # Fetch certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port)) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    x509_cert = x509.load_der_x509_certificate(cert, default_backend())
                    self._cache[hostname] = (x509_cert, time.time())
                    return self._get_cert_info(x509_cert)
        except Exception as e:
            error(f"SSL certificate check failed for {hostname}: {e}")
            return None

    def _get_cert_info(self, cert: x509.Certificate) -> Dict:
        """Extract information from an X.509 certificate.
        
        Args:
            cert: X.509 certificate object
            
        Returns:
            Dict containing certificate information
        """
        subject = cert.subject
        issuer = cert.issuer
        
        def get_attr_value(attrs, oid, default: str = "Unknown") -> str:
            """Safely get attribute value from certificate."""
            try:
                return attrs.get_attributes_for_oid(oid)[0].value
            except (IndexError, AttributeError):
                return default

        # Calculate days until expiration
        now = datetime.now()
        days_until_expiry = (cert.not_valid_after_utc - now).days

        return {
            "subject": {
                "common_name": get_attr_value(subject, NameOID.COMMON_NAME),
                "organization": get_attr_value(subject, NameOID.ORGANIZATION_NAME),
            },
            "issuer": {
                "common_name": get_attr_value(issuer, NameOID.COMMON_NAME),
                "organization": get_attr_value(issuer, NameOID.ORGANIZATION_NAME),
            },
            "not_before": cert.not_valid_before_utc.isoformat(),
            "not_after": cert.not_valid_after_utc.isoformat(),
            "days_until_expiry": days_until_expiry,
            "serial_number": cert.serial_number,
            "version": cert.version.name,
        }

    def get_cache_stats(self) -> Dict[str, int]:
        """Get SSL certificate cache statistics.
        
        Returns:
            Dict containing cache size and hit/miss counts
        """
        return {
            "size": len(self._cache),
            "entries": sum(1 for _, (_, timestamp) in self._cache.items()
                           if time.time() - timestamp < self._cache_ttl),
        }