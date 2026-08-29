# NetStabilizer

NetStabilizer là công cụ tối ưu hóa và ổn định kết nối mạng giữa 2 máy tính (P2P), được thiết kế cho các tác vụ yêu cầu độ trễ thấp như Remote Desktop (RDP, Moonlight, Parsec) và truyền tải dữ liệu dung lượng lớn qua Wi-Fi / Internet không ổn định.

Phần mềm kết hợp giữa việc can thiệp tối ưu TCP/IP Stack trên Windows và một đường hầm truyền tải UDP sử dụng giao thức KCP kết hợp cơ chế bù gói lỗi trước (Forward Error Correction - FEC).

---

## Tính năng chính

- **KCP ARQ Tunnel**: Chuyển tiếp luồng TCP qua kênh UDP với chu kỳ phản hồi 10ms, bỏ qua cơ chế nghẽn cổ chai của TCP truyền thống khi gặp độ trễ cao.
- **Zero-RTT FEC (10:3 Parity)**: Mã hóa bù gói lỗi phân tán. Khôi phục tức thì các gói tin bị mất trên đường truyền mà không cần đợi gửi lại (Retransmission RTT), giữ tốc độ và FPS ổn định.
- **Wi-Fi Anti-Ping-Spike**: Tự động vô hiệu hóa tính năng quét mạng nền (WLAN AutoConfig Background Scan) của Windows trong phiên làm việc, loại bỏ hiện tượng nhảy ping định kỳ (200-1000ms) trên Wi-Fi.
- **Windows TCP/IP Optimization**: Thiết lập `TCPNoDelay=1`, `TcpAckFrequency=1`, vô hiệu hóa `NetworkThrottlingIndex` và gắn nhãn QoS DSCP 46 (Expedited Forwarding) cho luồng dữ liệu remote.
- **Real-time Telemetry Dashboard**: Theo dõi độ trễ (RTT), độ biến thiên (Jitter), tỷ lệ mất gói và băng thông theo thời gian thực.
- **Zero Dependencies**: Chạy hoàn toàn trên thư viện chuẩn của Python 3, không yêu cầu cài đặt thêm các package bên thứ ba.

---

## Kiến trúc hoạt động

```text
[Máy A: Client]                             [Máy B: Server]
  Remote Client (RDP/Moonlight)               Remote Service (Port 3389/47989)
        | (Local TCP)                               ^ (Local TCP)
        v                                           |
  NetStabilizer Client                        NetStabilizer Server
        |                                           ^
        +===== [UDP Tunnel: KCP Fast ARQ + FEC] ====+
                     (Internet / Wi-Fi)
```

---

## Cấu trúc thư mục

```text
.
├── core/
│   ├── config.py          # Cấu hình tham số KCP, FEC và các preset
│   ├── fec.py             # Bộ mã hóa/giải mã XOR Multi-Parity FEC
│   ├── kcp.py             # Triển khai giao thức KCP ARQ
│   ├── optimizer.py       # Tối ưu hóa Registry, Netsh, WLAN scan và QoS
│   ├── telemetry.py       # Thu thập chỉ số mạng thời gian thực
│   └── tunnel.py          # Lõi proxy bất đồng bộ (asyncio)
├── gui/
│   └── app.py             # Giao diện điều khiển Tkinter Dark Theme
├── tests/
│   ├── test_fec.py        # Kiểm thử tính toán và phục hồi gói tin FEC
│   ├── test_kcp.py        # Kiểm thử truyền nhận và phân mảnh KCP
│   ├── test_optimizer.py  # Kiểm thử an toàn hệ thống
│   └── test_tunnel_e2e.py # Kiểm thử tích hợp Client <-> Server E2E
├── main.py                # Điểm khởi chạy chương trình (CLI / GUI)
├── run_gui.bat            # Khởi chạy giao diện đồ họa
├── optimize_network.bat   # Script chạy tối ưu hệ thống với quyền Admin
├── start_server.bat       # Khởi chạy nhanh Server Node
└── start_client.bat       # Khởi chạy nhanh Client Node
```

---

## Hướng dẫn sử dụng

### 1. Khởi chạy bằng Giao diện (GUI)

Chạy file `run_gui.bat` hoặc lệnh:

```bash
python main.py
```

1. **Tối ưu máy**: Nhấn nút **1-Click Tối ưu Registry & TCP Stack** và **Chặn Ping Spike Wi-Fi** (chỉ cần chạy một lần).
2. **Trên máy bị điều khiển (Server)**:
   - Chọn chế độ **Server (Máy chủ)**.
   - Chọn Preset (mặc định RDP cổng 3389).
   - Nhấn **Khởi chạy Tunnel**.
3. **Trên máy điều khiển (Client)**:
   - Chọn chế độ **Client (Điều khiển)**.
   - Nhập IP của máy Server vào ô **IP Máy chủ**.
   - Nhấn **Khởi chạy Tunnel**.
   - Mở Remote Desktop và kết nối tới địa chỉ: `127.0.0.1:13389`.

---

### 2. Khởi chạy qua Dòng lệnh (CLI / Headless)

Phù hợp khi chạy trên Windows Server hoặc tích hợp vào service nền.

**Trên máy Server (Máy bị điều khiển):**
```bash
python main.py --server --lport 29999 --rport 3389 --tport 29999
```

**Trên máy Client (Máy điều khiển):**
```bash
python main.py --client --host <SERVER_IP> --lport 13389 --tport 29999
```

**Tối ưu hóa nhanh Windows:**
```bash
python main.py --optimize
```

**Khôi phục cài đặt mạng mặc định:**
```bash
python main.py --restore
```

---

## Preset cổng thông dụng

| Ứng dụng | Cổng Remote gốc | Cổng Local Client | Cổng UDP Tunnel |
| :--- | :---: | :---: | :---: |
| **Windows RDP** | `3389` | `13389` | `29999` |
| **Moonlight / Sunshine** | `47989` | `47989` | `29998` |
| **Parsec** | `8000` | `18000` | `29997` |
| **SMB / File Transfer** | `445` | `14450` | `29996` |

---

## Kiểm thử

Chạy toàn bộ test suite bằng `unittest`:

```bash
python -m unittest discover tests -v
```
