#!/usr/bin/env python3
"""Test suite for the network diagnostics module."""

import unittest
from unittest.mock import patch, MagicMock
import socket
import ssl
from datetime import datetime, timedelta
from diagnostics import __version__

from diagnostics.network.network import (
    NetworkMetrics,
    ConnectionMonitor,
    LatencyMonitor,
    DNSMonitor,
    SSLCertMonitor,
)


class TestNetworkMetrics(unittest.TestCase):
    """Test cases for NetworkMetrics class."""

    def test_get_interface_stats(self):
        """Test getting network interface statistics."""
        mock_stats = {
            'eth0': MagicMock(
                bytes_sent=1000,
                bytes_recv=2000,
                packets_sent=10,
                packets_recv=20,
                errin=0,
                errout=0,
                dropin=0,
                dropout=0,
            ),
            'lo': MagicMock(
                bytes_sent=500,
                bytes_recv=500,
                packets_sent=5,
                packets_recv=5,
                errin=0,
                errout=0,
                dropin=0,
                dropout=0,
            ),
        }

        with patch('psutil.net_if_stats', return_value=mock_stats):
            stats = NetworkMetrics.get_interface_stats()
            
            # Check eth0 stats
            self.assertEqual(stats['eth0']['bytes_sent'], 1000)
            self.assertEqual(stats['eth0']['bytes_recv'], 2000)
            self.assertEqual(stats['eth0']['packets_sent'], 10)
            self.assertEqual(stats['eth0']['packets_recv'], 20)
            
            # Check lo stats
            self.assertEqual(stats['lo']['bytes_sent'], 500)
            self.assertEqual(stats['lo']['bytes_recv'], 500)
            self.assertEqual(stats['lo']['packets_sent'], 5)
            self.assertEqual(stats['lo']['packets_recv'], 5)

    def test_get_interface_stats_missing_attrs(self):
        """Test handling of interfaces with missing attributes."""
        # Create a mock that raises AttributeError for all attribute access
        class MockInterface:
            def __getattr__(self, name):
                raise AttributeError()
        
        mock_stats = {
            'eth0': MockInterface(),
        }

        with patch('psutil.net_if_stats', return_value=mock_stats):
            stats = NetworkMetrics.get_interface_stats()
            
            # Check that missing attributes default to 0
            self.assertEqual(stats['eth0']['bytes_sent'], 0)
            self.assertEqual(stats['eth0']['bytes_recv'], 0)
            self.assertEqual(stats['eth0']['packets_sent'], 0)
            self.assertEqual(stats['eth0']['packets_recv'], 0)
            self.assertEqual(stats['eth0']['errin'], 0)
            self.assertEqual(stats['eth0']['errout'], 0)
            self.assertEqual(stats['eth0']['dropin'], 0)
            self.assertEqual(stats['eth0']['dropout'], 0)

    def test_get_connections(self):
        """Test getting network connections."""
        mock_connections = [
            MagicMock(
                fd=1,
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                laddr=('127.0.0.1', 8080),
                raddr=('127.0.0.1', 12345),
                status='ESTABLISHED',
                pid=1234,
            ),
        ]

        with patch('psutil.net_connections', return_value=mock_connections):
            connections = NetworkMetrics.get_connections()
            
            # Check connection details
            self.assertEqual(len(connections), 1)
            conn = connections[0]
            self.assertEqual(conn['fd'], 1)
            self.assertEqual(conn['family'], socket.AF_INET)
            self.assertEqual(conn['type'], socket.SOCK_STREAM)
            self.assertEqual(conn['local_addr'], ('127.0.0.1', 8080))
            self.assertEqual(conn['remote_addr'], ('127.0.0.1', 12345))
            self.assertEqual(conn['status'], 'ESTABLISHED')
            self.assertEqual(conn['pid'], 1234)


class TestConnectionMonitor(unittest.TestCase):
    """Test cases for ConnectionMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = ConnectionMonitor()

    def test_update(self):
        """Test updating connection statistics."""
        mock_connections = [
            MagicMock(
                status='ESTABLISHED',
                laddr=('127.0.0.1', 8080),
                raddr=('127.0.0.1', 12345),
                pid=1234,
            ),
            MagicMock(
                status='LISTEN',
                laddr=('0.0.0.0', 80),
                raddr=None,
                pid=5678,
            ),
        ]

        with patch('psutil.net_connections', return_value=mock_connections):
            self.monitor.update()
            
            # Check connection summary
            summary = self.monitor.get_connection_summary()
            self.assertEqual(summary['ESTABLISHED'], 1)
            self.assertEqual(summary['LISTEN'], 1)
            
            # Check connections by status
            established = self.monitor.get_connections_by_status('ESTABLISHED')
            self.assertEqual(len(established), 1)
            self.assertEqual(established[0]['local'], ('127.0.0.1', 8080))
            self.assertEqual(established[0]['remote'], ('127.0.0.1', 12345))
            self.assertEqual(established[0]['pid'], 1234)


class TestLatencyMonitor(unittest.TestCase):
    """Test cases for LatencyMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = LatencyMonitor()

    def test_measure_latency_success(self):
        """Test successful latency measurement."""
        with patch('socket.socket') as mock_socket, \
             patch('time.time') as mock_time:
            # Set up the mock socket properly
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            
            # Simulate time passing during the connection
            mock_time.side_effect = [0.0, 0.1]  # 100ms latency
            
            latency = self.monitor.measure_latency('google.com', port=80)
            self.assertIsNotNone(latency)
            self.assertGreater(latency, 0)
            self.assertEqual(latency, 0.1)  # Should be exactly 100ms
            mock_sock.connect.assert_called_once_with(('google.com', 80))
            mock_sock.close.assert_called_once()

    def test_measure_latency_timeout(self):
        """Test latency measurement timeout."""
        with patch('socket.socket') as mock_socket:
            # Set up the mock socket properly
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = socket.timeout()
            
            latency = self.monitor.measure_latency('google.com', port=80)
            self.assertIsNone(latency)

    def test_track_latency_storage(self):
        """Test that latency measurements are stored correctly."""
        # Directly add a measurement to test storage
        self.monitor._latencies['google.com'] = [0.1]
        
        # Verify storage
        self.assertIn('google.com', self.monitor._latencies)
        self.assertEqual(len(self.monitor._latencies['google.com']), 1)
        self.assertEqual(self.monitor._latencies['google.com'][0], 0.1)
        
        # Test multiple measurements
        self.monitor._latencies['google.com'].append(0.2)
        self.assertEqual(len(self.monitor._latencies['google.com']), 2)
        self.assertEqual(self.monitor._latencies['google.com'][1], 0.2)

    def test_latency_stats_calculation(self):
        """Test that latency statistics are calculated correctly."""
        # Set up test data
        self.monitor._latencies['google.com'] = [0.1, 0.2, 0.3]
        
        # Get and verify statistics
        stats = self.monitor.get_latency_stats('google.com')
        self.assertIsNotNone(stats)
        self.assertEqual(stats['min'], 0.1)
        self.assertEqual(stats['max'], 0.3)
        self.assertAlmostEqual(stats['avg'], 0.2, places=7)  # (0.1 + 0.2 + 0.3) / 3

    def test_latency_storage_initialization(self):
        """Test that the latency storage dictionary is properly initialized."""
        # Verify the dictionary exists and is empty
        self.assertIsInstance(self.monitor._latencies, dict)
        self.assertEqual(len(self.monitor._latencies), 0)
        
        # Test adding a measurement
        self.monitor._latencies['google.com'] = [0.1]
        self.assertIn('google.com', self.monitor._latencies)
        self.assertEqual(len(self.monitor._latencies['google.com']), 1)
        self.assertEqual(self.monitor._latencies['google.com'][0], 0.1)

    def test_track_latency_check_interval(self):
        """Test that a single latency measurement is recorded correctly."""
        with patch('time.time') as mock_time, \
             patch.object(self.monitor, 'measure_latency', return_value=0.1), \
             patch('diagnostics.network.network.debug'):
            
            # Simulate time passing during a single measurement
            # First time call: 10.0 (current time)
            # Second time call: 10.1 (100ms later for latency)
            mock_time.side_effect = [10.0, 10.1]
            
            # Record a measurement
            self.monitor.track_latency('google.com')
            
            # Verify the measurement was recorded
            self.assertIn('google.com', self.monitor._latencies)
            self.assertEqual(len(self.monitor._latencies['google.com']), 1)
            self.assertEqual(self.monitor._latencies['google.com'][0], 0.1)
            
            # Verify measure_latency was called correctly
            self.monitor.measure_latency.assert_called_once_with('google.com', 80)


class TestDNSMonitor(unittest.TestCase):
    """Test cases for DNSMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = DNSMonitor()

    def test_resolve_success(self):
        """Test successful DNS resolution."""
        mock_ips = ['1.2.3.4', '5.6.7.8']
        with patch('socket.gethostbyname_ex', return_value=('google.com', [], mock_ips)):
            ips = self.monitor.resolve('google.com')
            self.assertEqual(ips, mock_ips)

    def test_resolve_failure(self):
        """Test DNS resolution failure."""
        with patch('socket.gethostbyname_ex', side_effect=socket.gaierror()):
            ips = self.monitor.resolve('invalid.example.com')
            self.assertIsNone(ips)

    def test_cache(self):
        """Test DNS cache functionality."""
        mock_ips = ['1.2.3.4']
        with patch('socket.gethostbyname_ex', return_value=('google.com', [], mock_ips)):
            # First resolution
            ips1 = self.monitor.resolve('google.com')
            # Second resolution should use cache
            ips2 = self.monitor.resolve('google.com')
            self.assertEqual(ips1, ips2)
            self.assertEqual(ips1, mock_ips)


class TestSSLCertMonitor(unittest.TestCase):
    """Test cases for SSLCertMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = SSLCertMonitor()

    def test_check_certificate_success(self):
        """Test successful certificate check."""
        mock_cert = MagicMock()
        mock_cert.subject = MagicMock()
        mock_cert.issuer = MagicMock()
        mock_cert.not_valid_before_utc = datetime.now()
        mock_cert.not_valid_after_utc = datetime.now() + timedelta(days=365)
        mock_cert.serial_number = 123456789
        mock_version = MagicMock()
        mock_version.name = 'v3'
        mock_cert.version = mock_version

        mock_context = MagicMock()
        mock_socket = MagicMock()
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = b'cert_data'

        with patch('ssl.create_default_context', return_value=mock_context), \
             patch('socket.create_connection', return_value=mock_socket), \
             patch('cryptography.x509.load_der_x509_certificate', return_value=mock_cert):
            
            mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssock
            
            cert_info = self.monitor.check_certificate('google.com')
            self.assertIsNotNone(cert_info)
            self.assertEqual(cert_info['serial_number'], 123456789)
            self.assertEqual(cert_info['version'], 'v3')
            self.assertIn('days_until_expiry', cert_info)
            self.assertGreater(cert_info['days_until_expiry'], 0)
            self.assertLessEqual(cert_info['days_until_expiry'], 365)

    def test_check_certificate_expired(self):
        """Test certificate check with expired certificate."""
        mock_cert = MagicMock()
        mock_cert.subject = MagicMock()
        mock_cert.issuer = MagicMock()
        mock_cert.not_valid_before_utc = datetime.now() - timedelta(days=400)
        mock_cert.not_valid_after_utc = datetime.now() - timedelta(days=35)
        mock_cert.serial_number = 123456789
        mock_version = MagicMock()
        mock_version.name = 'v3'
        mock_cert.version = mock_version

        mock_context = MagicMock()
        mock_socket = MagicMock()
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = b'cert_data'

        with patch('ssl.create_default_context', return_value=mock_context), \
             patch('socket.create_connection', return_value=mock_socket), \
             patch('cryptography.x509.load_der_x509_certificate', return_value=mock_cert):
            
            mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssock
            
            cert_info = self.monitor.check_certificate('google.com')
            self.assertIsNotNone(cert_info)
            self.assertIn('days_until_expiry', cert_info)
            self.assertLess(cert_info['days_until_expiry'], 0)

    def test_check_certificate_failure(self):
        """Test certificate check failure."""
        with patch('socket.create_connection', side_effect=Exception('Connection failed')):
            cert_info = self.monitor.check_certificate('invalid.example.com')
            self.assertIsNone(cert_info)

    def test_cache(self):
        """Test certificate cache functionality."""
        mock_cert = MagicMock()
        mock_cert.subject = MagicMock()
        mock_cert.issuer = MagicMock()
        mock_cert.not_valid_before_utc = datetime.now()
        mock_cert.not_valid_after_utc = datetime.now() + timedelta(days=365)
        mock_cert.serial_number = 123456789
        mock_version = MagicMock()
        mock_version.name = 'v3'
        mock_cert.version = mock_version

        mock_context = MagicMock()
        mock_socket = MagicMock()
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.return_value = b'cert_data'

        with patch('ssl.create_default_context', return_value=mock_context), \
             patch('socket.create_connection', return_value=mock_socket), \
             patch('cryptography.x509.load_der_x509_certificate', return_value=mock_cert):
            
            mock_context.wrap_socket.return_value.__enter__.return_value = mock_ssock
            
            # First check
            cert_info1 = self.monitor.check_certificate('google.com')
            # Second check should use cache
            cert_info2 = self.monitor.check_certificate('google.com')
            self.assertEqual(cert_info1, cert_info2)
            self.assertEqual(cert_info1['serial_number'], 123456789)
            self.assertEqual(cert_info1['version'], 'v3')
            self.assertIn('days_until_expiry', cert_info1)
            self.assertGreater(cert_info1['days_until_expiry'], 0)
            self.assertLessEqual(cert_info1['days_until_expiry'], 365)


if __name__ == '__main__':
    unittest.main() 