"""
Unit tests for KCP ARQ transmission, MTU segmentation, and ACK handling
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kcp import KCP

class TestKCP(unittest.TestCase):
    def test_kcp_send_recv_loopback(self):
        """Simulates 2 KCP endpoints exchanging data over virtual wire"""
        client_to_server_wire = []
        server_to_client_wire = []

        kcp_client = KCP(12345, lambda data: client_to_server_wire.append(data))
        kcp_server = KCP(12345, lambda data: server_to_client_wire.append(data))

        kcp_client.set_nodelay(1, 10, 2, 1)
        kcp_server.set_nodelay(1, 10, 2, 1)

        payload = b"Hello Low Latency Remote Desktop via KCP!"
        kcp_client.send(payload)
        kcp_client.flush()

        # Wire transfer client -> server
        for pkt in client_to_server_wire:
            kcp_server.input(pkt)
        client_to_server_wire.clear()

        # Server polls receive
        received = kcp_server.recv()
        self.assertEqual(received, payload)

        # Server sends ACK back
        kcp_server.flush()
        for pkt in server_to_client_wire:
            kcp_client.input(pkt)
        server_to_client_wire.clear()

        # Client buffer should be cleared after ACK
        self.assertEqual(len(kcp_client.snd_buf), 0)

    def test_kcp_mtu_segmentation(self):
        """Verifies large payload segmentation based on configured MTU"""
        out_packets = []
        kcp = KCP(9999, lambda data: out_packets.append(data))
        kcp.set_mtu(500) # Small MTU
        
        large_data = b"X" * 1200
        kcp.send(large_data)
        kcp.flush()

        # With MTU=500 and MSS=476, 1200 bytes should be split into 3 segments
        self.assertEqual(len(out_packets), 3)

if __name__ == "__main__":
    unittest.main()
