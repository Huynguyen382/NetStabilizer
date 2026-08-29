"""
End-to-End integration test for NetStabilizer Tunnel Node (Client <-> Server over KCP+FEC)
"""

import asyncio
import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import TunnelConfig, FECConfig, KCPConfig
from core.tunnel import TunnelNode
from core.telemetry import TelemetryTracker

class TestTunnelE2E(unittest.IsolatedAsyncioTestCase):
    async def test_end_to_end_tcp_over_kcp_tunnel(self):
        """
        Spawns:
        1. Mock Echo TCP Server on port 39001 (representing RDP service)
        2. NetStabilizer Server Node on UDP 39002 (bridging to 39001)
        3. NetStabilizer Client Node on Local TCP 39003 -> Tunnel UDP 39002
        4. Test Client connecting to 39003, sending data, and receiving echo
        """
        # 1. Start Mock Echo Service
        async def handle_echo(reader, writer):
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(b"ECHO:" + data)
                await writer.drain()
            writer.close()
            await writer.wait_closed()

        echo_server = await asyncio.start_server(handle_echo, "127.0.0.1", 39001)

        # 2. Start NetStabilizer Server Node
        server_cfg = TunnelConfig(
            mode="server",
            listen_host="127.0.0.1",
            listen_port=39002,
            remote_host="127.0.0.1",
            remote_port=39001,
            tunnel_port=39002,
            fec=FECConfig(enabled=True, data_shards=5, parity_shards=2),
            kcp=KCPConfig(nodelay=1, interval=10, resend=2, nc=1)
        )
        server_node = TunnelNode(server_cfg, TelemetryTracker())
        await server_node.start()

        # 3. Start NetStabilizer Client Node
        client_cfg = TunnelConfig(
            mode="client",
            listen_host="127.0.0.1",
            listen_port=39003,
            remote_host="127.0.0.1",
            remote_port=39001,
            tunnel_port=39002,
            fec=FECConfig(enabled=True, data_shards=5, parity_shards=2),
            kcp=KCPConfig(nodelay=1, interval=10, resend=2, nc=1)
        )
        client_node = TunnelNode(client_cfg, TelemetryTracker())
        await client_node.start()

        # 4. Connect to Client Local Port (39003) and send payload
        reader, writer = await asyncio.open_connection("127.0.0.1", 39003)
        test_payload = b"TestingNetStabilizerThroughputStreamPayload_12345"
        writer.write(test_payload)
        await writer.drain()

        # Wait for echo reply
        response = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        self.assertEqual(response, b"ECHO:" + test_payload)

        # Teardown
        writer.close()
        await writer.wait_closed()
        await client_node.stop()
        await server_node.stop()
        echo_server.close()
        await echo_server.wait_closed()

if __name__ == "__main__":
    unittest.main()
