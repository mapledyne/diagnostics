#!/usr/bin/env python3
"""Test suite for the main diagnostics module."""

import unittest
from unittest.mock import patch
import json
import sys
from io import StringIO

from diagnostics.__main__ import main


class TestDiagnostics(unittest.TestCase):
    """Test cases for the main diagnostics module."""

    def setUp(self):
        """Set up test fixtures."""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.stdout = StringIO()
        self.stderr = StringIO()
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def tearDown(self):
        """Clean up test fixtures."""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def test_metrics_command(self):
        """Test the metrics command output."""
        # Mock the Metrics class methods
        with patch('diagnostics.Metrics.memory_usage') as mock_memory, \
             patch('diagnostics.Metrics.cpu_percent') as mock_cpu, \
             patch('diagnostics.Metrics.thread_count') as mock_threads, \
             patch('diagnostics.Metrics.uptime') as mock_uptime, \
             patch('diagnostics.Metrics.uptime_friendly') as mock_uptime_friendly:
            
            # Set mock return values
            mock_memory.return_value = 1024 * 1024  # 1MB
            mock_cpu.return_value = 50.0
            mock_threads.return_value = 10
            mock_uptime.return_value = 3600
            mock_uptime_friendly.return_value = "1 hour"

            # Test without JSON flag
            sys.argv = ['diagnostics', 'metrics']
            main()
            output = self.stdout.getvalue()
            
            # Verify output contains expected values
            self.assertIn("memory_usage: 1048576", output)
            self.assertIn("cpu_percent: 50.0", output)
            self.assertIn("thread_count: 10", output)
            self.assertIn("app uptime (should be close to 0 if run from CLI): 3600", output)
            self.assertIn("app uptime_friendly: 1 hour", output)

            # Test with JSON flag
            self.stdout.seek(0)
            self.stdout.truncate()
            sys.argv = ['diagnostics', 'metrics', '--json']
            main()
            output = self.stdout.getvalue()
            
            # Parse JSON output
            data = json.loads(output)
            self.assertEqual(data['memory_usage'], 1048576)
            self.assertEqual(data['cpu_percent'], 50.0)
            self.assertEqual(data['thread_count'], 10)
            self.assertEqual(data['app uptime (should be close to 0 if run from CLI)'], 3600)
            self.assertEqual(data['app uptime_friendly'], "1 hour")

    def test_network_command_help(self):
        """Test the network command help output."""
        sys.argv = ['diagnostics', 'network']
        main()
        output = self.stdout.getvalue()
        self.assertIn("usage: diagnostics network", output)
        self.assertIn("Available network commands", output)
        self.assertIn("metrics", output)
        self.assertIn("connections", output)
        self.assertIn("latency", output)
        self.assertIn("dns", output)
        self.assertIn("ssl", output)

    def test_invalid_command(self):
        """Test handling of invalid command."""
        sys.argv = ['diagnostics', 'invalid_command']
        with patch('argparse.ArgumentParser.print_help') as mock_help, \
             patch('argparse.ArgumentParser.parse_args',
                  side_effect=SystemExit(2)):
            main()
            mock_help.assert_called_once()

    def test_no_command(self):
        """Test handling of no command provided."""
        sys.argv = ['diagnostics']
        with patch('argparse.ArgumentParser.print_help') as mock_help:
            main()
            mock_help.assert_called_once()

    def test_network_metrics_command(self):
        """Test the network metrics command."""
        with patch('diagnostics.network.__main__.main') as mock_network_main:
            mock_network_main.return_value = 0
            sys.argv = ['diagnostics', 'network', 'metrics']
            main()
            mock_network_main.assert_called_once()

    def test_network_latency_command(self):
        """Test the network latency command."""
        with patch('diagnostics.network.__main__.main') as mock_network_main:
            mock_network_main.return_value = 0
            sys.argv = ['diagnostics', 'network', 'latency', 'google.com']
            main()
            mock_network_main.assert_called_once()


if __name__ == '__main__':
    unittest.main() 