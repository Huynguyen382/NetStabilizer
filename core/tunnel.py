"""
NetStabilizer - Asynchronous KCP + FEC Turbo Tunnel Engine
Provides bidirectional TCP proxying through a stabilized, low-jitter KCP/UDP tunnel with Forward Error Correction.
"""

import asyncio
import struct
import time
from typing import Dict, Optional, Tuple

from core.config import TunnelConfig
from core.fec import FECEncoder, FECDecoder
from core.kcp import KCP
from core.telemetry import TelemetryTracker

HEARTBEAT_MAGIC = 0xA1B2C3D4
HEARTBEAT_STRUCT = struct.Struct("!IIQ") # Magic(4B), Seq(4B), Timestamp_ms(8B)

class UDPProtocol(asyncio.DatagramProtocol):
    """Low-overhead asyncio UDP protocol handler"""
    def __init__(self, on_packet_cb):
        self.on_packet_cb = on_packet_cb
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        self.on_packet_cb(data, addr)

    def error_received(self, exc: Exception):
        pass


class TunnelNode:
    """
    Manages the lifecycle of the KCP+FEC Tunnel for either Client or Server mode.
    """
    def __init__(self, config: TunnelConfig, telemetry: Optional[TelemetryTracker] = None):
        self.config = config
        self.telemetry = telemetry or TelemetryTracker()
        self.is_running = False
        
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.udp_transport: Optional[asyncio.DatagramTransport] = None
        self.tcp_server: Optional[asyncio.Server] = None
        
        # FEC layers
        self.fec_encoder = FECEncoder(config.fec.data_shards, config.fec.parity_shards) if config.fec.enabled else None
        self.fec_decoder = FECDecoder() if config.fec.enabled else None
        
        # Remote endpoint address for client mode
        self.remote_addr: Optional[Tuple[str, int]] = None
        
        # Connection map: conv -> {kcp, addr, tcp_reader, tcp_writer, last_active}
        self.sessions: Dict[int, Dict] = {}
        self.conv_counter = 1000
        
        # Periodic tasks
        self._update_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_seq = 0

    # -------------------------------------------------------------
    # Startup and Shutdown
    # -------------------------------------------------------------
    async def start(self):
        """Starts the tunnel node"""
        self.loop = asyncio.get_running_loop()
        self.is_running = True
        self.telemetry.status = f"Running ({self.config.mode.upper()})"
        
        # 1. Start UDP Datagram transport
        if self.config.mode == "client":
            self.remote_addr = (self.config.remote_host, self.config.tunnel_port)
            transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPProtocol(self._on_udp_packet_received),
                local_addr=("0.0.0.0", 0)
            )
            self.udp_transport = transport
            
            # Start TCP listener for local applications (e.g. localhost:13389)
            self.tcp_server = await asyncio.start_server(
                self._handle_local_tcp_connection,
                host=self.config.listen_host,
                port=self.config.listen_port
            )
            
            # Start Heartbeat sender
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        else: # Server mode
            # Bind server UDP on tunnel_port
            transport, _ = await self.loop.create_datagram_endpoint(
                lambda: UDPProtocol(self._on_udp_packet_received),
                local_addr=("0.0.0.0", self.config.tunnel_port)
            )
            self.udp_transport = transport

        # Start KCP clock tick task (10ms interval)
        self._update_task = asyncio.create_task(self._kcp_clock_loop())
        # Start stale session cleanup task (every 10s)
        self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())

    async def stop(self):
        """Gracefully shuts down all listeners and sockets"""
        self.is_running = False
        self.telemetry.status = "Stopped"
        
        for task in [self._heartbeat_task, self._update_task, self._cleanup_task]:
            if task:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            
        if self.tcp_server:
            self.tcp_server.close()
            await self.tcp_server.wait_closed()
            
        if self.udp_transport:
            self.udp_transport.close()
            
        # Close all active TCP writers
        for s in list(self.sessions.values()):
            writer = s.get('tcp_writer')
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
        self.sessions.clear()
        self.telemetry.active_connections = 0

    # -------------------------------------------------------------
    # UDP Transport & FEC Layer
    # -------------------------------------------------------------
    def _send_raw_udp(self, data: bytes, target_addr: Tuple[str, int]):
        """Encodes with FEC if enabled, and dispatches to UDP transport"""
        if not self.udp_transport or self.udp_transport.is_closing():
            return
            
        if self.fec_encoder:
            packets = self.fec_encoder.encode_packet(data)
            for pkt in packets:
                self.udp_transport.sendto(pkt, target_addr)
                self.telemetry.record_bytes_sent(len(pkt))
        else:
            self.udp_transport.sendto(data, target_addr)
            self.telemetry.record_bytes_sent(len(data))

    def _on_udp_packet_received(self, raw_data: bytes, addr: Tuple[str, int]):
        """Decodes FEC and feeds to KCP or Heartbeat handler"""
        self.telemetry.record_bytes_recv(len(raw_data))
        
        # Check if packet is a Heartbeat packet
        if len(raw_data) == HEARTBEAT_STRUCT.size:
            try:
                magic, seq, ts = HEARTBEAT_STRUCT.unpack(raw_data)
                if magic == HEARTBEAT_MAGIC:
                    self._handle_heartbeat(seq, ts, addr)
                    return
            except Exception:
                pass

        # FEC Decoding
        if self.fec_decoder:
            decoded_packets, recovered_count = self.fec_decoder.decode_packet(raw_data)
            if recovered_count > 0:
                self.telemetry.record_fec_recovered(recovered_count)
        else:
            decoded_packets = [raw_data]

        for pkt in decoded_packets:
            self._handle_kcp_packet(pkt, addr)

    # -------------------------------------------------------------
    # Heartbeat & Telemetry RTT Measurement
    # -------------------------------------------------------------
    async def _heartbeat_loop(self):
        """Sends periodic lightweight UDP pings to measure RTT and prevent NAT timeout"""
        while self.is_running:
            if self.remote_addr and self.udp_transport and not self.udp_transport.is_closing():
                self._heartbeat_seq += 1
                now_ms = int(time.monotonic() * 1000) & 0xFFFFFFFFFFFFFFFF
                pkt = HEARTBEAT_STRUCT.pack(HEARTBEAT_MAGIC, self._heartbeat_seq, now_ms)
                self.udp_transport.sendto(pkt, self.remote_addr)
            await asyncio.sleep(self.config.heartbeat_interval)

    def _handle_heartbeat(self, seq: int, ts_ms: int, addr: Tuple[str, int]):
        if self.config.mode == "server":
            if self.udp_transport and not self.udp_transport.is_closing():
                pkt = HEARTBEAT_STRUCT.pack(HEARTBEAT_MAGIC, seq, ts_ms)
                self.udp_transport.sendto(pkt, addr)
        else:
            now_ms = int(time.monotonic() * 1000) & 0xFFFFFFFFFFFFFFFF
            rtt = max(0.0, float(now_ms - ts_ms))
            if rtt < 5000:
                self.telemetry.record_ping(rtt)

    # -------------------------------------------------------------
    # KCP Session Management
    # -------------------------------------------------------------
    def _create_kcp_instance(self, conv: int, target_addr: Tuple[str, int]) -> KCP:
        def kcp_output(buf: bytes):
            self._send_raw_udp(buf, target_addr)

        kcp = KCP(conv, kcp_output)
        kcp.set_nodelay(
            nodelay=self.config.kcp.nodelay,
            interval=self.config.kcp.interval,
            resend=self.config.kcp.resend,
            nc=self.config.kcp.nc
        )
        kcp.snd_wnd = self.config.kcp.sndwnd
        kcp.rcv_wnd = self.config.kcp.rcvwnd
        kcp.set_mtu(self.config.kcp.mtu)
        kcp.stream = self.config.kcp.stream
        return kcp

    def _handle_kcp_packet(self, data: bytes, addr: Tuple[str, int]):
        if len(data) < 24:
            return
        conv = struct.unpack_from("!I", data, 0)[0]
        
        if conv not in self.sessions:
            if self.config.mode == "server":
                kcp = self._create_kcp_instance(conv, addr)
                self.sessions[conv] = {
                    'kcp': kcp,
                    'addr': addr,
                    'tcp_reader': None,
                    'tcp_writer': None,
                    'last_active': time.monotonic()
                }
                asyncio.create_task(self._connect_to_backend_service(conv))
            else:
                return

        session = self.sessions[conv]
        session['last_active'] = time.monotonic()
        session['kcp'].input(data)
        
        # If writer is ready, route data immediately
        writer = session.get('tcp_writer')
        if writer and not writer.is_closing():
            payload = session['kcp'].recv()
            if payload:
                writer.write(payload)

    # -------------------------------------------------------------
    # TCP Stream Bridging
    # -------------------------------------------------------------
    async def _handle_local_tcp_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Client Mode: Handles local application TCP connection (e.g. RDP client)"""
        conv = self.conv_counter
        self.conv_counter = (self.conv_counter + 1) & 0x7FFFFFFF
        
        kcp = self._create_kcp_instance(conv, self.remote_addr)
        self.sessions[conv] = {
            'kcp': kcp,
            'addr': self.remote_addr,
            'tcp_reader': reader,
            'tcp_writer': writer,
            'last_active': time.monotonic()
        }
        self.telemetry.active_connections = len(self.sessions)

        try:
            while self.is_running:
                data = await reader.read(4096)
                if not data:
                    break
                kcp.send(data)
                kcp.flush()
                session = self.sessions.get(conv)
                if session:
                    session['last_active'] = time.monotonic()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            if conv in self.sessions:
                del self.sessions[conv]
            self.telemetry.active_connections = len(self.sessions)

    async def _connect_to_backend_service(self, conv: int):
        """Server Mode: Connects to local destination service (e.g. RDP 3389)"""
        session = self.sessions.get(conv)
        if not session:
            return
            
        try:
            reader, writer = await asyncio.open_connection(
                self.config.remote_host,
                self.config.remote_port
            )
            session['tcp_reader'] = reader
            session['tcp_writer'] = writer
            self.telemetry.active_connections = len(self.sessions)

            # Flush any pending received data upon connection establishment
            pending = session['kcp'].recv()
            if pending:
                writer.write(pending)

            while self.is_running and conv in self.sessions:
                data = await reader.read(4096)
                if not data:
                    break
                session['kcp'].send(data)
                session['kcp'].flush()
                session['last_active'] = time.monotonic()
        except Exception:
            pass
        finally:
            if conv in self.sessions:
                if session.get('tcp_writer'):
                    try:
                        session['tcp_writer'].close()
                        await session['tcp_writer'].wait_closed()
                    except Exception:
                        pass
                del self.sessions[conv]
            self.telemetry.active_connections = len(self.sessions)

    # -------------------------------------------------------------
    # KCP Clock Tick Loop & Session Cleanup
    # -------------------------------------------------------------
    async def _kcp_clock_loop(self):
        """Updates all KCP state machines at high resolution interval (10ms)"""
        while self.is_running:
            for s in list(self.sessions.values()):
                kcp = s.get('kcp')
                if kcp:
                    kcp.update()
                    # Drain received data cleanly only if writer is ready
                    writer = s.get('tcp_writer')
                    if writer and not writer.is_closing():
                        data = kcp.recv()
                        if data:
                            try:
                                writer.write(data)
                            except Exception:
                                pass
            await asyncio.sleep(self.config.kcp.interval / 1000.0)

    async def _session_cleanup_loop(self):
        """Cleans up stale sessions inactive for more than 60 seconds"""
        while self.is_running:
            await asyncio.sleep(10.0)
            now = time.monotonic()
            stale = [
                conv for conv, s in list(self.sessions.items())
                if now - s.get('last_active', 0) > 60.0
            ]
            for conv in stale:
                s = self.sessions.pop(conv, None)
                if s and s.get('tcp_writer'):
                    try:
                        s['tcp_writer'].close()
                    except Exception:
                        pass
            if stale:
                self.telemetry.active_connections = len(self.sessions)
