"""
Unit tests for Network Optimizer helper inspection
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.optimizer import NetworkOptimizer

class TestOptimizer(unittest.TestCase):
    def test_admin_check_runs(self):
        """Ensures is_admin() executes safely without unhandled exceptions"""
        result = NetworkOptimizer.is_admin()
        self.assertIsInstance(result, bool)

    def test_get_wifi_interfaces(self):
        """Ensures Wi-Fi interfaces can be queried safely"""
        ifaces = NetworkOptimizer.get_wifi_interfaces()
        self.assertIsInstance(ifaces, list)

if __name__ == "__main__":
    unittest.main()
