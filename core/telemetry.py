"""
NetStabilizer - Telemetry & Quality Engine
Low-overhead real-time metrics for Ping, Jitter, Packet Loss, and Bandwidth Throughput.
Thread-safe for cross-thread GUI / tunnel telemetry sharing.
"""

import time
import threading
from collections import deque
from dataclasses import dataclass

@dataclass
class QualityMetrics:
    ping_ms: float = 0.0
    min_ping_ms: float = 0.0
    max_ping_ms: float = 0.0
    avg_ping_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    fec_recovered_count: int = 0
    upload_speed_kbps: float = 0.0
    download_speed_kbps: float = 0.0
    total_bytes_sent: int = 0
    total_bytes_recv: int = 0
    active_connections: int = 0
    status: str = "Idle"

class TelemetryTracker:
    """
    Maintains a rolling window of network measurements with negligible CPU overhead.
    All mutating methods are thread-safe via a lightweight lock.
    """
    def __init__(self, history_size: int = 60):
        self._lock = threading.Lock()
        self.history_size = history_size
        self.ping_history: deque[float] = deque(maxlen=history_size)
        
        # Byte counters
        self.bytes_sent: int = 0
        self.bytes_recv: int = 0
        self._last_bytes_sent: int = 0
        self._last_bytes_recv: int = 0
        self._last_speed_check: float = time.monotonic()
        
        # Packet counters
        self.packets_sent: int = 0
        self.packets_recv: int = 0
        self.packets_lost: int = 0
        self.fec_recovered: int = 0
        
        # Current speeds
        self._upload_speed: float = 0.0
        self._download_speed: float = 0.0
        
        # Active connections
        self.active_connections: int = 0
        self.status: str = "Ready"

    def record_ping(self, rtt_ms: float):
        """Records an RTT sample in milliseconds"""
        if rtt_ms >= 0:
            with self._lock:
                self.ping_history.append(rtt_ms)

    def record_bytes_sent(self, count: int):
        with self._lock:
            self.bytes_sent += count
            self.packets_sent += 1

    def record_bytes_recv(self, count: int):
        with self._lock:
            self.bytes_recv += count
            self.packets_recv += 1

    def record_fec_recovered(self, count: int = 1):
        with self._lock:
            self.fec_recovered += count

    def record_packet_loss(self, count: int = 1):
        with self._lock:
            self.packets_lost += count

    def get_metrics(self) -> QualityMetrics:
        """Computes instantaneous and statistical metrics (thread-safe snapshot)"""
        with self._lock:
            now = time.monotonic()
            dt = max(0.001, now - self._last_speed_check)
            
            # Recalculate bandwidth speed periodically
            if dt >= 0.5:
                self._upload_speed = ((self.bytes_sent - self._last_bytes_sent) / dt) / 1024.0
                self._download_speed = ((self.bytes_recv - self._last_bytes_recv) / dt) / 1024.0
                self._last_bytes_sent = self.bytes_sent
                self._last_bytes_recv = self.bytes_recv
                self._last_speed_check = now

            # Ping & Jitter stats from snapshot
            pings = list(self.ping_history)
            upload_speed = self._upload_speed
            download_speed = self._download_speed
            bytes_sent = self.bytes_sent
            bytes_recv = self.bytes_recv
            packets_lost = self.packets_lost
            packets_sent = self.packets_sent
            fec_recovered = self.fec_recovered
            active_conns = self.active_connections
            status = self.status

        # Compute stats outside the lock
        if pings:
            cur_ping = pings[-1]
            min_ping = min(pings)
            max_ping = max(pings)
            avg_ping = sum(pings) / len(pings)
            
            # RFC 3550 Jitter: mean absolute difference between consecutive delays
            if len(pings) > 1:
                jitter = sum(abs(pings[i] - pings[i - 1]) for i in range(1, len(pings))) / (len(pings) - 1)
            else:
                jitter = 0.0
        else:
            cur_ping = min_ping = max_ping = avg_ping = jitter = 0.0

        # Packet loss calculation
        total_expected = packets_sent + packets_lost
        loss_pct = (packets_lost / total_expected * 100.0) if total_expected > 0 else 0.0

        return QualityMetrics(
            ping_ms=round(cur_ping, 1),
            min_ping_ms=round(min_ping, 1),
            max_ping_ms=round(max_ping, 1),
            avg_ping_ms=round(avg_ping, 1),
            jitter_ms=round(jitter, 1),
            packet_loss_pct=round(min(100.0, loss_pct), 2),
            fec_recovered_count=fec_recovered,
            upload_speed_kbps=round(upload_speed, 1),
            download_speed_kbps=round(download_speed, 1),
            total_bytes_sent=bytes_sent,
            total_bytes_recv=bytes_recv,
            active_connections=active_conns,
            status=status
        )
