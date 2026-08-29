"""
NetStabilizer - Modern GUI Application
Professional dark-themed control center for network stabilization, real-time telemetry, and Windows optimization.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import asyncio
import time
from typing import Optional, List

from core.config import TunnelConfig, FECConfig, KCPConfig, PRESETS
from core.optimizer import NetworkOptimizer
from core.telemetry import TelemetryTracker
from core.tunnel import TunnelNode

# Color Palette (Modern Dark Theme)
BG_DARK = "#121316"
BG_CARD = "#1B1D22"
BG_CARD_LIGHT = "#24272E"
TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#8E95A5"
ACCENT_GREEN = "#00D26A"
ACCENT_CYAN = "#00D8F6"
ACCENT_ORANGE = "#FF9900"
ACCENT_RED = "#F85149"
BORDER_COLOR = "#2D3139"

class NetStabilizerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NetStabilizer - Low Latency & Network Optimizer")
        self.root.geometry("880x720")
        self.root.minsize(800, 650)
        self.root.configure(bg=BG_DARK)

        self.telemetry = TelemetryTracker()
        self.tunnel_node: Optional[TunnelNode] = None
        self.tunnel_thread: Optional[threading.Thread] = None
        self.tunnel_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_tunnel_running = False

        # GUI State Variables
        self.var_mode = tk.StringVar(value="client")
        self.var_preset = tk.StringVar(value=list(PRESETS.keys())[0])
        self.var_remote_host = tk.StringVar(value="192.168.1.100")
        self.var_listen_port = tk.StringVar(value="13389")
        self.var_remote_port = tk.StringVar(value="3389")
        self.var_tunnel_port = tk.StringVar(value="29999")
        self.var_fec_enabled = tk.BooleanVar(value=True)
        self.var_wifi_anti_lag = tk.BooleanVar(value=False)

        self._setup_styles()
        self._build_ui()
        self._on_preset_changed()

        # Start periodic UI refresh timer (200ms)
        self.root.after(200, self._refresh_telemetry_ui)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure general styles
        style.configure("TFrame", background=BG_DARK)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=BG_CARD, foreground=TEXT_MUTED, font=("Segoe UI", 8))
        style.configure("Header.TLabel", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Segoe UI", 11, "bold"))
        style.configure("MetricVal.TLabel", background=BG_CARD, foreground=ACCENT_CYAN, font=("Segoe UI", 16, "bold"))
        
        # Entries and Combobox
        style.configure("TCombobox", fieldbackground=BG_CARD_LIGHT, background=BG_CARD_LIGHT, foreground=TEXT_PRIMARY)
        style.configure("TCheckbutton", background=BG_CARD, foreground=TEXT_PRIMARY, font=("Segoe UI", 9))

    def _build_ui(self):
        # Header banner
        header_frame = tk.Frame(self.root, bg=BG_CARD, height=60, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        header_frame.pack(fill="x", padx=12, pady=(10, 6))

        title_lbl = tk.Label(header_frame, text="⚡ NETSTABILIZER", bg=BG_CARD, fg=ACCENT_CYAN, font=("Segoe UI", 14, "bold"))
        title_lbl.pack(side="left", padx=16, pady=8)

        sub_lbl = tk.Label(header_frame, text="Zero-RTT FEC Tunnel & Windows Anti-Lag Optimizer", bg=BG_CARD, fg=TEXT_MUTED, font=("Segoe UI", 9))
        sub_lbl.pack(side="left", padx=4, pady=8)

        self.status_badge = tk.Label(header_frame, text="● IDLE", bg=BG_CARD_LIGHT, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.status_badge.pack(side="right", padx=16, pady=8)

        # Main Layout: 2 Columns
        main_container = tk.Frame(self.root, bg=BG_DARK)
        main_container.pack(fill="both", expand=True, padx=12, pady=4)

        left_panel = tk.Frame(main_container, bg=BG_DARK, width=380)
        left_panel.pack(side="left", fill="both", expand=False, padx=(0, 6))

        right_panel = tk.Frame(main_container, bg=BG_DARK)
        right_panel.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # --- LEFT PANEL: Settings & Optimization ---
        self._build_optimizer_card(left_panel)
        self._build_tunnel_config_card(left_panel)

        # --- RIGHT PANEL: Real-time Telemetry & Graph ---
        self._build_telemetry_metrics_card(right_panel)
        self._build_graph_card(right_panel)
        self._build_log_card(right_panel)

    def _build_optimizer_card(self, parent):
        card = tk.LabelFrame(parent, text=" 🚀 TỐI ƯU HÓA HỆ THỐNG WINDOWS ", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), bd=1, relief="solid")
        card.pack(fill="x", pady=(0, 8), padx=2, ipady=6)

        is_admin = NetworkOptimizer.is_admin()
        admin_text = "Quyền Admin: ĐÃ CÓ ✓" if is_admin else "Quyền Admin: CHƯA CÓ ⚠ (Cần chạy Run as Admin để sửa Registry)"
        admin_color = ACCENT_GREEN if is_admin else ACCENT_ORANGE
        admin_lbl = tk.Label(card, text=admin_text, bg=BG_CARD, fg=admin_color, font=("Segoe UI", 8, "bold"))
        admin_lbl.pack(anchor="w", padx=12, pady=(4, 6))

        btn_opt = tk.Button(
            card, text="⚡ 1-Click Tối ưu Registry & TCP Stack",
            bg="#1f402b", fg=ACCENT_GREEN, activebackground="#2a573a", activeforeground=TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self._action_optimize_windows
        )
        btn_opt.pack(fill="x", padx=12, pady=3)

        self.btn_wifi = tk.Button(
            card, text="🛡 Chặn Ping Spike Wi-Fi (Tắt Background Scan)",
            bg="#233547", fg=ACCENT_CYAN, activebackground="#314b63", activeforeground=TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2", command=self._action_toggle_wifi_scan
        )
        self.btn_wifi.pack(fill="x", padx=12, pady=3)

        btn_restore = tk.Button(
            card, text="↺ Khôi phục cài đặt mạng mặc định",
            bg="#362224", fg=ACCENT_RED, activebackground="#4d3033", activeforeground=TEXT_PRIMARY,
            font=("Segoe UI", 8), relief="flat", cursor="hand2", command=self._action_restore_defaults
        )
        btn_restore.pack(fill="x", padx=12, pady=3)

    def _build_tunnel_config_card(self, parent):
        card = tk.LabelFrame(parent, text=" ⚙ CẤU HÌNH KCP/UDP TUNNEL ", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), bd=1, relief="solid")
        card.pack(fill="both", expand=True, pady=(0, 2), padx=2, ipady=4)

        # Mode Selection
        mode_frame = tk.Frame(card, bg=BG_CARD)
        mode_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(mode_frame, text="Chế độ:", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(side="left")
        
        rb_client = tk.Radiobutton(mode_frame, text="Client (Điều khiển)", variable=self.var_mode, value="client", bg=BG_CARD, fg=TEXT_PRIMARY, selectcolor=BG_CARD_LIGHT, activebackground=BG_CARD, command=self._on_mode_changed)
        rb_client.pack(side="left", padx=8)
        rb_server = tk.Radiobutton(mode_frame, text="Server (Máy chủ)", variable=self.var_mode, value="server", bg=BG_CARD, fg=TEXT_PRIMARY, selectcolor=BG_CARD_LIGHT, activebackground=BG_CARD, command=self._on_mode_changed)
        rb_server.pack(side="left", padx=4)

        # Preset Selection
        tk.Label(card, text="Mẫu cấu hình sẵn (Preset):", bg=BG_CARD, fg=TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(4, 0))
        cb_preset = ttk.Combobox(card, textvariable=self.var_preset, values=list(PRESETS.keys()), state="readonly")
        cb_preset.pack(fill="x", padx=12, pady=(2, 6))
        cb_preset.bind("<<ComboboxSelected>>", lambda e: self._on_preset_changed())

        # Inputs
        input_grid = tk.Frame(card, bg=BG_CARD)
        input_grid.pack(fill="x", padx=12, pady=2)

        self.lbl_remote_host = tk.Label(input_grid, text="IP Máy chủ (Remote IP):", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 8))
        self.lbl_remote_host.grid(row=0, column=0, sticky="w", pady=2)
        self.entry_remote_host = tk.Entry(input_grid, textvariable=self.var_remote_host, bg=BG_CARD_LIGHT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, relief="flat")
        self.entry_remote_host.grid(row=0, column=1, sticky="ew", pady=2, padx=(4, 0))

        tk.Label(input_grid, text="Cổng ứng dụng đích:", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.entry_remote_port = tk.Entry(input_grid, textvariable=self.var_remote_port, bg=BG_CARD_LIGHT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, relief="flat", width=10)
        self.entry_remote_port.grid(row=1, column=1, sticky="w", pady=2, padx=(4, 0))

        self.lbl_listen_port = tk.Label(input_grid, text="Cổng lắng nghe Local:", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 8))
        self.lbl_listen_port.grid(row=2, column=0, sticky="w", pady=2)
        self.entry_listen_port = tk.Entry(input_grid, textvariable=self.var_listen_port, bg=BG_CARD_LIGHT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, relief="flat", width=10)
        self.entry_listen_port.grid(row=2, column=1, sticky="w", pady=2, padx=(4, 0))

        tk.Label(input_grid, text="Cổng UDP KCP Tunnel:", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 8)).grid(row=3, column=0, sticky="w", pady=2)
        self.entry_tunnel_port = tk.Entry(input_grid, textvariable=self.var_tunnel_port, bg=BG_CARD_LIGHT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, relief="flat", width=10)
        self.entry_tunnel_port.grid(row=3, column=1, sticky="w", pady=2, padx=(4, 0))

        input_grid.columnconfigure(1, weight=1)

        # FEC checkbox
        cb_fec = tk.Checkbutton(card, text="Bật bù gói lỗi tức thì (Zero-RTT FEC 10:3)", variable=self.var_fec_enabled, bg=BG_CARD, fg=TEXT_PRIMARY, selectcolor=BG_CARD_LIGHT, activebackground=BG_CARD)
        cb_fec.pack(anchor="w", padx=12, pady=(6, 8))

        # Start / Stop Tunnel Button
        self.btn_toggle_tunnel = tk.Button(
            card, text="▶ KHỞI CHẠY TUNNEL",
            bg=ACCENT_GREEN, fg="#000000", activebackground="#00b359", activeforeground="#000000",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", command=self._action_toggle_tunnel
        )
        self.btn_toggle_tunnel.pack(fill="x", padx=12, pady=(4, 6))

    def _build_telemetry_metrics_card(self, parent):
        card = tk.LabelFrame(parent, text=" 📊 TRẠNG THÁI & CHẤT LƯỢNG MẠNG THỜI GIAN THỰC ", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), bd=1, relief="solid")
        card.pack(fill="x", pady=(0, 6), padx=2, ipady=4)

        grid = tk.Frame(card, bg=BG_CARD)
        grid.pack(fill="x", padx=12, pady=4)

        # Metric 1: Ping / Latency
        m1 = tk.Frame(grid, bg=BG_CARD_LIGHT, bd=1, relief="solid")
        m1.grid(row=0, column=0, padx=4, pady=2, sticky="nsew")
        tk.Label(m1, text="PING / LATENCY", bg=BG_CARD_LIGHT, fg=TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_ping_val = tk.Label(m1, text="-- ms", bg=BG_CARD_LIGHT, fg=ACCENT_GREEN, font=("Segoe UI", 14, "bold"))
        self.lbl_ping_val.pack(anchor="w", padx=8, pady=(0, 4))

        # Metric 2: Jitter
        m2 = tk.Frame(grid, bg=BG_CARD_LIGHT, bd=1, relief="solid")
        m2.grid(row=0, column=1, padx=4, pady=2, sticky="nsew")
        tk.Label(m2, text="JITTER (BIẾN ĐỘNG)", bg=BG_CARD_LIGHT, fg=TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_jitter_val = tk.Label(m2, text="-- ms", bg=BG_CARD_LIGHT, fg=ACCENT_CYAN, font=("Segoe UI", 14, "bold"))
        self.lbl_jitter_val.pack(anchor="w", padx=8, pady=(0, 4))

        # Metric 3: Packet Loss & FEC
        m3 = tk.Frame(grid, bg=BG_CARD_LIGHT, bd=1, relief="solid")
        m3.grid(row=0, column=2, padx=4, pady=2, sticky="nsew")
        tk.Label(m3, text="RỚT GÓI / FEC PHỤC HỒI", bg=BG_CARD_LIGHT, fg=TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_loss_val = tk.Label(m3, text="0% (0 pkt)", bg=BG_CARD_LIGHT, fg=ACCENT_ORANGE, font=("Segoe UI", 13, "bold"))
        self.lbl_loss_val.pack(anchor="w", padx=8, pady=(0, 4))

        # Metric 4: Throughput (Speed)
        m4 = tk.Frame(grid, bg=BG_CARD_LIGHT, bd=1, relief="solid")
        m4.grid(row=0, column=3, padx=4, pady=2, sticky="nsew")
        tk.Label(m4, text="TỐC ĐỘ UP / DOWN", bg=BG_CARD_LIGHT, fg=TEXT_MUTED, font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.lbl_speed_val = tk.Label(m4, text="0 / 0 KB/s", bg=BG_CARD_LIGHT, fg=TEXT_PRIMARY, font=("Segoe UI", 13, "bold"))
        self.lbl_speed_val.pack(anchor="w", padx=8, pady=(0, 4))

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)
        grid.columnconfigure(3, weight=1)

    def _build_graph_card(self, parent):
        card = tk.LabelFrame(parent, text=" 📈 BIỂU ĐỒ ĐỘ TRỄ (PING CHART) ", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), bd=1, relief="solid")
        card.pack(fill="x", pady=(0, 6), padx=2)

        self.canvas_graph = tk.Canvas(card, bg="#0E1013", height=130, bd=0, highlightthickness=0)
        self.canvas_graph.pack(fill="x", padx=8, pady=6)

    def _build_log_card(self, parent):
        card = tk.LabelFrame(parent, text=" 📋 NHẬT KÝ HOẠT ĐỘNG (LOGS) ", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), bd=1, relief="solid")
        card.pack(fill="both", expand=True, pady=(0, 2), padx=2)

        self.txt_log = tk.Text(card, bg="#0E1013", fg="#C9D1D9", font=("Consolas", 8), bd=0, relief="flat", wrap="word", height=6)
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=6)
        self.log("NetStabilizer sẵn sàng. Nhấn 'Tối ưu hóa Windows' hoặc khởi chạy Tunnel.")

    def log(self, msg: str):
        """Thread-safe log dispatcher"""
        def _do_log():
            t_str = time.strftime("%H:%M:%S")
            self.txt_log.insert("end", f"[{t_str}] {msg}\n")
            self.txt_log.see("end")
        self.root.after(0, _do_log)

    # -------------------------------------------------------------
    # Event Handlers & Preset Management
    # -------------------------------------------------------------
    def _on_preset_changed(self):
        preset_name = self.var_preset.get()
        if preset_name in PRESETS:
            p = PRESETS[preset_name]
            self.var_listen_port.set(str(p["listen_port"]))
            self.var_remote_port.set(str(p["remote_port"]))
            self.var_tunnel_port.set(str(p["tunnel_port"]))
            self.log(f"Đã nạp preset '{preset_name}': {p['description']}")

    def _on_mode_changed(self):
        mode = self.var_mode.get()
        if mode == "client":
            self.lbl_remote_host.config(text="IP Máy chủ (Remote IP):")
            self.entry_remote_host.config(state="normal")
            self.lbl_listen_port.config(text="Cổng lắng nghe Local:")
        else:
            self.lbl_remote_host.config(text="IP Ứng dụng đích (Target Host):")
            self.var_remote_host.set("127.0.0.1")
            self.lbl_listen_port.config(text="Cổng UDP Server:")

    # -------------------------------------------------------------
    # Optimization Actions
    # -------------------------------------------------------------
    def _action_optimize_windows(self):
        self.log("Đang tiến hành tối ưu hóa TCP/IP Stack, Registry và Netsh...")
        
        ok1, msg1 = NetworkOptimizer.apply_tcp_registry_tweaks()
        self.log(msg1)
        
        ok2, msg2 = NetworkOptimizer.apply_netsh_optimizations()
        self.log(msg2)
        
        try:
            r_port = int(self.var_remote_port.get().strip() or "3389")
            t_port = int(self.var_tunnel_port.get().strip() or "29999")
        except ValueError:
            r_port, t_port = 3389, 29999

        ok3, msg3 = NetworkOptimizer.apply_qos_policy([r_port, t_port])
        self.log(msg3)

        if ok1:
            messagebox.showinfo("Thành công", "Đã tối ưu hóa hoàn tất TCP/IP & Network Responsiveness!")

    def _action_toggle_wifi_scan(self):
        # Current state: False means scan is enabled (default). Toggling turns anti-lag ON (disables scan).
        new_anti_lag_state = not self.var_wifi_anti_lag.get()
        self.var_wifi_anti_lag.set(new_anti_lag_state)
        
        # When anti-lag is ON -> autoconfig scan is NO
        ok, msg = NetworkOptimizer.set_wifi_autoconfig(enabled=not new_anti_lag_state)
        self.log(msg)
        if ok:
            if new_anti_lag_state:
                self.btn_wifi.config(text="🛡 ĐÃ BẬT Chặn Ping Spike Wi-Fi", bg="#1f402b", fg=ACCENT_GREEN)
            else:
                self.btn_wifi.config(text="🛡 Chặn Ping Spike Wi-Fi (Tắt Background Scan)", bg="#233547", fg=ACCENT_CYAN)
            status_txt = "ĐÃ BẬT Chặn Ping Spike Wi-Fi" if new_anti_lag_state else "Đã tắt chặn Wi-Fi (Bật lại quét ngầm)"
            messagebox.showinfo("Wi-Fi Anti-Lag", f"{status_txt}\n{msg}")

    def _action_restore_defaults(self):
        if messagebox.askyesno("Khôi phục mặc định", "Bạn có chắc chắn muốn khôi phục toàn bộ cài đặt mạng Windows về ban đầu?"):
            ok, msg = NetworkOptimizer.restore_defaults()
            self.var_wifi_anti_lag.set(False)
            self.btn_wifi.config(text="🛡 Chặn Ping Spike Wi-Fi (Tắt Background Scan)", bg="#233547", fg=ACCENT_CYAN)
            self.log(msg)
            messagebox.showinfo("Khôi phục", "Đã hoàn tất khôi phục cài đặt mạng mặc định.")

    # -------------------------------------------------------------
    # Tunnel Controls
    # -------------------------------------------------------------
    def _action_toggle_tunnel(self):
        if not self.is_tunnel_running:
            self._start_tunnel()
        else:
            self._stop_tunnel()

    def _start_tunnel(self):
        try:
            lport = int(self.var_listen_port.get().strip())
            rport = int(self.var_remote_port.get().strip())
            tport = int(self.var_tunnel_port.get().strip())
            rhost = self.var_remote_host.get().strip()

            if not rhost:
                raise ValueError("Vui lòng nhập IP máy chủ!")
            if not (1 <= lport <= 65535 and 1 <= rport <= 65535 and 1 <= tport <= 65535):
                raise ValueError("Cổng kết nối phải nằm trong khoảng 1-65535!")

            cfg = TunnelConfig(
                mode=self.var_mode.get(),
                listen_host="127.0.0.1" if self.var_mode.get() == "client" else "0.0.0.0",
                listen_port=lport,
                remote_host=rhost,
                remote_port=rport,
                tunnel_port=tport,
                fec=FECConfig(enabled=self.var_fec_enabled.get(), data_shards=10, parity_shards=3),
                kcp=KCPConfig(nodelay=1, interval=10, resend=2, nc=1)
            )
        except ValueError as e:
            messagebox.showerror("Lỗi cấu hình", f"Vui lòng kiểm tra lại thông số kết nối:\n{e}")
            return

        self.is_tunnel_running = True
        self.btn_toggle_tunnel.config(text="■ DỪNG TUNNEL", bg=ACCENT_RED, fg=TEXT_PRIMARY)
        self.status_badge.config(text=f"● {cfg.mode.upper()} ĐANG CHẠY", bg="#1b3824", fg=ACCENT_GREEN)

        def runner():
            self.tunnel_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.tunnel_loop)
            self.tunnel_node = TunnelNode(cfg, self.telemetry)
            self.tunnel_loop.run_until_complete(self.tunnel_node.start())
            self.log(f"Tunnel [{cfg.mode.upper()}] đã khởi chạy trên port UDP {cfg.tunnel_port}")
            if cfg.mode == "client":
                self.log(f"-> Hãy mở ứng dụng Remote kết nối tới địa chỉ: 127.0.0.1:{cfg.listen_port}")
            try:
                self.tunnel_loop.run_forever()
            except Exception:
                pass

        self.tunnel_thread = threading.Thread(target=runner, daemon=True)
        self.tunnel_thread.start()

    def _stop_tunnel(self):
        self.is_tunnel_running = False
        if self.tunnel_node and self.tunnel_loop:
            asyncio.run_coroutine_threadsafe(self.tunnel_node.stop(), self.tunnel_loop)
            self.tunnel_loop.call_soon_threadsafe(self.tunnel_loop.stop)
            
        self.btn_toggle_tunnel.config(text="▶ KHỞI CHẠY TUNNEL", bg=ACCENT_GREEN, fg="#000000")
        self.status_badge.config(text="● ĐÃ DỪNG", bg=BG_CARD_LIGHT, fg=TEXT_MUTED)
        self.log("Tunnel đã dừng.")

    # -------------------------------------------------------------
    # Periodic Telemetry & Graph Refresh
    # -------------------------------------------------------------
    def _refresh_telemetry_ui(self):
        metrics = self.telemetry.get_metrics()
        
        # Update Ping badge
        if metrics.ping_ms > 0:
            p_color = ACCENT_GREEN if metrics.ping_ms < 35 else (ACCENT_ORANGE if metrics.ping_ms < 80 else ACCENT_RED)
            self.lbl_ping_val.config(text=f"{metrics.ping_ms} ms", fg=p_color)
        else:
            self.lbl_ping_val.config(text="-- ms", fg=TEXT_MUTED)

        self.lbl_jitter_val.config(text=f"± {metrics.jitter_ms} ms")
        self.lbl_loss_val.config(text=f"{metrics.packet_loss_pct}% (FEC: +{metrics.fec_recovered_count})")
        self.lbl_speed_val.config(text=f"↑ {metrics.upload_speed_kbps} / ↓ {metrics.download_speed_kbps} KB/s")

        # Redraw Latency Graph
        self._draw_graph(list(self.telemetry.ping_history))

        # Schedule next refresh
        self.root.after(200, self._refresh_telemetry_ui)

    def _draw_graph(self, history: List[float]):
        self.canvas_graph.delete("all")
        w = self.canvas_graph.winfo_width()
        h = self.canvas_graph.winfo_height()
        if w < 10 or h < 10:
            return

        # Grid lines
        for y_pct in [0.25, 0.5, 0.75]:
            y = int(h * y_pct)
            self.canvas_graph.create_line(0, y, w, y, fill="#1c2028", dash=(2, 4))

        if not history:
            self.canvas_graph.create_text(w // 2, h // 2, text="Đang đợi kết nối để vẽ biểu đồ Ping...", fill=TEXT_MUTED, font=("Segoe UI", 9))
            return

        max_val = max(50.0, max(history) * 1.2)
        step_x = w / max(1, len(history) - 1) if len(history) > 1 else w

        points = []
        for i, val in enumerate(history):
            x = int(i * step_x)
            y = int(h - (val / max_val) * (h - 20) - 10)
            points.extend([x, y])

        if len(points) >= 4:
            # Draw line
            self.canvas_graph.create_line(points, fill=ACCENT_CYAN, width=2, smooth=True)
            # Draw latest point circle
            last_x, last_y = points[-2], points[-1]
            self.canvas_graph.create_oval(last_x - 4, last_y - 4, last_x + 4, last_y + 4, fill=ACCENT_GREEN, outline="#FFFFFF")
