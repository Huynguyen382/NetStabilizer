"""
NetStabilizer - Configuration Module
Defines settings, presets, and constants for high-performance network tunneling and optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class FECConfig:
    """Forward Error Correction Configuration (Parity-based loss recovery)"""
    enabled: bool = True
    data_shards: int = 10     # Number of original data packets per group
    parity_shards: int = 3   # Number of redundant parity packets generated (handles loss instantly)

@dataclass
class KCPConfig:
    """KCP ARQ Protocol Tuning Parameters"""
    nodelay: int = 1         # 1: Enable nodelay mode (no ACK delay)
    interval: int = 10       # Internal update clock interval in ms (10ms for minimal jitter)
    resend: int = 2          # Fast retransmit trigger threshold (2 ACK duplicates)
    nc: int = 1              # 1: Disable congestion window (constant aggressive pacing), 0: Enable
    sndwnd: int = 128        # Send window size in packets
    rcvwnd: int = 128        # Receive window size in packets
    mtu: int = 1400          # Maximum Transmission Unit (optimized for internet UDP without fragmentation)
    stream: bool = True      # Stream mode

@dataclass
class TunnelConfig:
    """Tunnel Connection Configuration"""
    mode: str = "client"     # 'server' or 'client'
    listen_host: str = "127.0.0.1"
    listen_port: int = 13389 # Local port exposed to the user / remote desktop app
    remote_host: str = "127.0.0.1" # Target server IP for client, or target service for server
    remote_port: int = 3389  # Target port (e.g., 3389 for RDP)
    tunnel_port: int = 29999 # UDP port used for KCP/FEC transport between the 2 machines
    heartbeat_interval: float = 2.0 # Keep-alive ping interval in seconds
    fec: FECConfig = field(default_factory=FECConfig)
    kcp: KCPConfig = field(default_factory=KCPConfig)

# Preset definitions for popular remote desktop and gaming tools
PRESETS: Dict[str, Dict[str, Any]] = {
    "RDP (Windows Remote Desktop)": {
        "listen_port": 13389,
        "remote_port": 3389,
        "tunnel_port": 29999,
        "description": "Forward local port 13389 qua KCP tunnel toi port 3389 (RDP) cua may dich"
    },
    "Moonlight / Sunshine Game Stream": {
        "listen_port": 47989,
        "remote_port": 47989,
        "tunnel_port": 29998,
        "description": "Toi uu hoa duong truyen video stream do tre thap cho Moonlight"
    },
    "Parsec Remote": {
        "listen_port": 18000,
        "remote_port": 8000,
        "tunnel_port": 29997,
        "description": "Ho tro tunnel Parsec peer-to-peer"
    },
    "High-Speed File Transfer (SMB/TCP)": {
        "listen_port": 14450,
        "remote_port": 445,
        "tunnel_port": 29996,
        "description": "On dinh bang thong download/upload file dung luong lon, giam suy hao do mat goi"
    },
    "Custom Port": {
        "listen_port": 10080,
        "remote_port": 80,
        "tunnel_port": 29995,
        "description": "Tuy chinh cong chuyen tiep bat ky"
    }
}
