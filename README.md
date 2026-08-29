# ⚡ NetStabilizer - Ổn Định Ping & Tốc Độ Truyền Tải Khi Remote

**NetStabilizer** là giải pháp tối ưu hóa mạng hiệu năng cao, chuyên biệt cho **Remote Desktop** (RDP, Parsec, Moonlight, Sunshine, AnyDesk, UltraViewer) và **truyền tải dữ liệu tốc độ cao** giữa 2 máy tính qua mạng Internet/Wi-Fi không ổn định.

---

## 🎯 Vấn Đề Được Giải Quyết Triệt Để

1. **Ping Spike trên Wi-Fi (Nhảy Ping từ 10ms lên 500-1000ms mỗi 60s)**:
   - *Nguyên nhân*: Windows WLAN AutoConfig tự động quét sóng Wi-Fi ngầm liên tục để tìm mạng mới, gây nghẽn và ngắt quãng luồng truyền tải.
   - *Giải pháp*: **Anti-Ping Spike Engine** vô hiệu hóa quét nền khi đang trong session kết nối, giữ ping phẳng tuyệt đối.

2. **Rớt gói (Packet Loss) & Hiện tượng Khựng hình (Stutter / Bufferbloat)**:
   - *Nguyên nhân*: Giao thức TCP truyền thống khi gặp rớt gói 1-5% sẽ dừng luồng (Head-of-Line Blocking) và đợi phản hồi ACK (mất 1-3 RTT).
   - *Giải pháp*: **KCP ARQ Fast Mode + Zero-RTT Forward Error Correction (FEC)**. Tự động bù gói tin bị mất tức thì bằng thuật toán Parity (10:3) mà không cần chờ gửi lại, giảm thiểu triệt để độ trễ.

3. **Nagle Algorithm & Windows Network Throttling**:
   - Tối ưu hóa Registry: `TCPNoDelay=1`, `TcpAckFrequency=1`, `NetworkThrottlingIndex=0xFFFFFFFF`, `SystemResponsiveness=0` (xử lý gói tin phím/chuột tức thì 0ms delay).
   - Đánh dấu **DSCP 46 (Expedited Forwarding)** ưu tiên gói tin Remote ở cấp độ router/card mạng.

---

## 📂 Cấu Trúc Mã Nguồn Chuẩn Hóa

```text
d:\Stable internet connection\
│
├── core\
│   ├── __init__.py
│   ├── config.py             # Cấu hình Tunnel, FEC, KCP parameters & Presets
│   ├── fec.py                # Thuật toán Forward Error Correction (Bù gói lỗi Zero-RTT)
│   ├── kcp.py                # Giao thức KCP ARQ siêu nhanh cho đường truyền UDP
│   ├── optimizer.py          # Module can thiệp Registry, Netsh, WLAN AutoConfig, QoS
│   ├── telemetry.py          # Bộ đo lường RTT, Jitter, Packet Loss, Throughput thời gian thực
│   └── tunnel.py             # Lõi Asyncio UDP/TCP Tunnel Node Client & Server
│
├── gui\
│   ├── __init__.py
│   └── app.py                # Giao diện Desktop Dark Mode hiện đại, đồ thị Ping Real-time
│
├── tests\
│   ├── test_fec.py           # Unit tests kiểm tra khả năng phục hồi khi rớt gói
│   ├── test_kcp.py           # Unit tests kiểm tra truyền nhận dữ liệu KCP
│   └── test_optimizer.py     # Unit tests kiểm tra module tối ưu hóa Windows
│
├── main.py                   # Điểm khởi chạy chính (hỗ trợ cả GUI và dòng lệnh CLI)
├── run_gui.bat               # Khởi chạy giao diện đồ họa GUI
├── optimize_network.bat      # 1-Click tối ưu hóa toàn diện mạng Windows (yêu cầu Admin)
├── start_server.bat          # Khởi chạy Server Node nhanh (trên máy bị điều khiển)
├── start_client.bat          # Khởi chạy Client Node nhanh (trên máy điều khiển)
└── README.md
```

---

## 🚀 Hướng Dẫn Sử Dụng

### Cách 1: Sử dụng Giao diện Đồ họa (Khuyến khích)
Chạy file `run_gui.bat` hoặc lệnh:
```bash
python main.py
```
- **Bước 1**: Nhấn nút `⚡ 1-Click Tối ưu Registry & TCP Stack` và `🛡 Chặn Ping Spike Wi-Fi` trên cả 2 máy.
- **Bước 2 (Trên Máy B - Máy bị điều khiển)**: Chọn chế độ **Server (Máy chủ)** -> Nhấn `▶ KHỞI CHẠY TUNNEL`.
- **Bước 3 (Trên Máy A - Máy điều khiển)**: Chọn chế độ **Client (Điều khiển)** -> Nhập IP của Máy B -> Nhấn `▶ KHỞI CHẠY TUNNEL`.
- **Bước 4**: Mở ứng dụng Remote Desktop (hoặc RDP), gõ địa chỉ kết nối là `127.0.0.1:13389`. Toàn bộ luồng dữ liệu sẽ được truyền qua kênh KCP+FEC siêu ổn định.

---

### Cách 2: Sử dụng Dòng Lệnh / Batch Scripts
- **Trên Máy B (Server/Remote Host)**:
  ```bash
  start_server.bat
  # hoặc: python main.py --server --lport 29999 --rport 3389 --tport 29999
  ```
- **Trên Máy A (Client/Remote User)**:
  ```bash
  start_client.bat
  # hoặc: python main.py --client --host <IP_MAY_B> --lport 13389 --tport 29999
  ```
- **Tối ưu hóa nhanh Windows bằng CLI**:
  ```bash
  python main.py --optimize
  ```
- **Khôi phục cấu hình Windows ban đầu**:
  ```bash
  python main.py --restore
  ```

---

## 🧪 Kiểm Thử & Đánh Giá

Chạy toàn bộ bộ kiểm thử tự động:
```bash
python -m unittest discover tests -v
```
Toàn bộ mã nguồn sử dụng thư viện chuẩn của Python 3, không yêu cầu cài đặt thêm các thư viện cồng kềnh, đảm bảo khởi động tức thì và chiếm dụng RAM/CPU cực thấp (< 0.5% CPU).
