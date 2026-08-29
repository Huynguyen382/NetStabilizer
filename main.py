"""
NetStabilizer - Main Entrypoint
Supports graphical GUI mode and headless CLI/Service modes.
"""

import sys
import os
import argparse
import asyncio

# Ensure workspace directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import TunnelConfig, FECConfig, KCPConfig
from core.optimizer import NetworkOptimizer
from core.tunnel import TunnelNode
from core.telemetry import TelemetryTracker

def run_cli_optimize():
    print("=" * 60)
    print("⚡ NetStabilizer - Windows Network & Wi-Fi Optimizer")
    print("=" * 60)
    ok1, msg1 = NetworkOptimizer.apply_tcp_registry_tweaks()
    print(msg1)
    ok2, msg2 = NetworkOptimizer.apply_netsh_optimizations()
    print(msg2)
    ok3, msg3 = NetworkOptimizer.apply_qos_policy([3389, 29999, 47989])
    print(msg3)
    ok4, msg4 = NetworkOptimizer.set_wifi_autoconfig(enabled=False)
    print(msg4)
    print("=" * 60)
    print("✓ Đã hoàn tất tối ưu hóa toàn diện mạng Windows!")

def run_cli_restore():
    print("=" * 60)
    print("↺ NetStabilizer - Khôi phục cài đặt mạng Windows mặc định")
    print("=" * 60)
    ok, msg = NetworkOptimizer.restore_defaults()
    print(msg)
    print("=" * 60)

async def _async_run_tunnel(cfg: TunnelConfig):
    telemetry = TelemetryTracker()
    node = TunnelNode(cfg, telemetry)
    await node.start()
    print(f"✓ Tunnel [{cfg.mode.upper()}] đang hoạt động trên UDP {cfg.tunnel_port}. Nhấn Ctrl+C để dừng.")
    if cfg.mode == "client":
        print(f"-> Mở Remote Desktop kết nối tới: {cfg.listen_host}:{cfg.listen_port}")
    try:
        while True:
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass
    finally:
        await node.stop()
        print("✓ Đã dừng tunnel.")

def run_cli_tunnel(mode: str, remote_host: str, listen_port: int, remote_port: int, tunnel_port: int, fec: bool):
    print("=" * 60)
    print(f"⚡ NetStabilizer KCP+FEC Tunnel Node [{mode.upper()}]")
    print(f"• Listen: {listen_port} -> Remote: {remote_host}:{remote_port}")
    print(f"• UDP Tunnel Port: {tunnel_port} | FEC: {'Bật (10:3)' if fec else 'Tắt'}")
    print("=" * 60)
    
    cfg = TunnelConfig(
        mode=mode,
        listen_host="127.0.0.1" if mode == "client" else "0.0.0.0",
        listen_port=listen_port,
        remote_host=remote_host,
        remote_port=remote_port,
        tunnel_port=tunnel_port,
        fec=FECConfig(enabled=fec, data_shards=10, parity_shards=3),
        kcp=KCPConfig(nodelay=1, interval=10, resend=2, nc=1)
    )
    
    try:
        asyncio.run(_async_run_tunnel(cfg))
    except KeyboardInterrupt:
        print("\nĐã nhận tín hiệu dừng từ người dùng.")

def run_gui():
    import tkinter as tk
    from gui.app import NetStabilizerGUI
    root = tk.Tk()
    app = NetStabilizerGUI(root)
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="NetStabilizer - Ultra Low Latency Network Optimizer & KCP/FEC Tunnel")
    parser.add_argument("--gui", action="store_true", help="Launch GUI interface (default)")
    parser.add_argument("--server", action="store_true", help="Run in Headless Server mode")
    parser.add_argument("--client", action="store_true", help="Run in Headless Client mode")
    parser.add_argument("--optimize", action="store_true", help="Apply 1-Click Windows TCP/IP & Wi-Fi tweaks")
    parser.add_argument("--restore", action="store_true", help="Restore Windows network default settings")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Remote host IP")
    parser.add_argument("--lport", type=int, default=13389, help="Local listen port")
    parser.add_argument("--rport", type=int, default=3389, help="Remote target port")
    parser.add_argument("--tport", type=int, default=29999, help="KCP UDP tunnel port")
    parser.add_argument("--no-fec", action="store_true", help="Disable FEC packet redundancy")

    args = parser.parse_args()

    if args.optimize:
        run_cli_optimize()
    elif args.restore:
        run_cli_restore()
    elif args.server:
        run_cli_tunnel("server", args.host, args.lport, args.rport, args.tport, not args.no_fec)
    elif args.client:
        run_cli_tunnel("client", args.host, args.lport, args.rport, args.tport, not args.no_fec)
    else:
        run_gui()

if __name__ == "__main__":
    main()
