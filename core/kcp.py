"""
NetStabilizer - High Performance KCP ARQ Protocol Implementation
Ultra-low latency ARQ transport over UDP with configurable fast retransmission,
aggressive ACK dispatching, and selective repeat windowing.
"""

import struct
import time
from collections import deque
from typing import List, Tuple, Callable

# Standard KCP Packet Header Specification (24 bytes):
# [conv: 4B][cmd: 1B][frg: 1B][wnd: 2B][ts: 4B][sn: 4B][una: 4B][len: 4B]
KCP_HEADER_FORMAT = "!IBBHIIII"
KCP_HEADER_SIZE = struct.calcsize(KCP_HEADER_FORMAT)  # exactly 24 bytes

# Commands
IKCP_CMD_PUSH = 81  # Data push
IKCP_CMD_ACK  = 82  # Acknowledge
IKCP_CMD_WASK = 83  # Window probe ask
IKCP_CMD_WINS = 84  # Window probe tell

class KCPSegment:
    __slots__ = ('conv', 'cmd', 'frg', 'wnd', 'ts', 'sn', 'una', 'data', 'resendts', 'rto', 'fastack', 'xmit')
    def __init__(self, conv=0, cmd=0, frg=0, wnd=0, ts=0, sn=0, una=0, data=b''):
        self.conv = conv
        self.cmd = cmd
        self.frg = frg
        self.wnd = wnd
        self.ts = ts
        self.sn = sn
        self.una = una
        self.data = data
        self.resendts = 0
        self.rto = 0
        self.fastack = 0
        self.xmit = 0

    def encode(self) -> bytes:
        hdr = struct.pack(KCP_HEADER_FORMAT, self.conv, self.cmd, self.frg, self.wnd, self.ts, self.sn, self.una, len(self.data))
        return hdr + self.data

class KCP:
    """
    KCP Protocol Control Block
    """
    def __init__(self, conv: int, output_fn: Callable[[bytes], None]):
        self.conv = conv
        self.output = output_fn
        
        self.snd_una = 0
        self.snd_nxt = 0
        self.rcv_nxt = 0
        
        self.rx_rttval = 0
        self.rx_srtt = 0
        self.rx_rto = 200 # Default 200ms
        self.rx_minrto = 10 # Minimal RTO in ms
        
        self.snd_wnd = 128
        self.rcv_wnd = 128
        self.rmt_wnd = 128
        self.cwnd = 0
        self.incr = 0
        
        self.interval = 10 # Update interval in ms
        self.ts_flush = 0
        self.nodelay = 1
        self.updated = False
        self.fastresend = 2
        self.nocwnd = 1
        self.stream = True
        self.mtu = 1400
        self.mss = self.mtu - KCP_HEADER_SIZE
        
        # Use deque for O(1) popleft instead of list.pop(0)
        self.snd_queue: deque[KCPSegment] = deque()
        self.rcv_queue: deque[KCPSegment] = deque()
        self.snd_buf: List[KCPSegment] = []
        self.rcv_buf: List[KCPSegment] = []
        self.acklist: List[Tuple[int, int]] = [] # (sn, ts)
        
        self.state = 0

    @staticmethod
    def current_ms() -> int:
        return int(time.monotonic() * 1000) & 0xFFFFFFFF

    def set_nodelay(self, nodelay=1, interval=10, resend=2, nc=1):
        self.nodelay = nodelay
        self.interval = max(5, min(interval, 5000))
        self.fastresend = resend
        self.nocwnd = nc
        self.rx_minrto = 10 if nodelay else 30

    def set_mtu(self, mtu: int):
        """Sets MTU and recalculates MSS"""
        self.mtu = mtu
        self.mss = self.mtu - KCP_HEADER_SIZE

    def send(self, data: bytes) -> int:
        """Pushes application data into send queue, segmenting by MSS"""
        if not data:
            return -1
        
        offset = 0
        length = len(data)
        
        while offset < length:
            chunk_size = min(self.mss, length - offset)
            chunk = data[offset:offset + chunk_size]
            offset += chunk_size
            
            seg = KCPSegment(
                conv=self.conv,
                cmd=IKCP_CMD_PUSH,
                frg=0,
                wnd=0,
                ts=0,
                sn=0,
                una=0,
                data=chunk
            )
            self.snd_queue.append(seg)
        return 0

    def recv(self) -> bytes:
        """Pulls received ordered data from receive queue"""
        if not self.rcv_queue:
            return b''
        
        chunks = []
        while self.rcv_queue:
            seg = self.rcv_queue.popleft()
            chunks.append(seg.data)
            if not self.stream:
                break
        return b''.join(chunks)

    def input(self, data: bytes) -> int:
        """Parses incoming lower-layer UDP packet into KCP segments"""
        if len(data) < KCP_HEADER_SIZE:
            return -1
        
        offset = 0
        size = len(data)
        current = self.current_ms()
        
        while offset + KCP_HEADER_SIZE <= size:
            conv, cmd, frg, wnd, ts, sn, una, dlen = struct.unpack_from(KCP_HEADER_FORMAT, data, offset)
            offset += KCP_HEADER_SIZE
            
            if conv != self.conv or offset + dlen > size:
                return -1
            
            payload = data[offset:offset + dlen]
            offset += dlen
            
            self.rmt_wnd = wnd
            self._parse_una(una)
            self._shrink_buf()
            
            if cmd == IKCP_CMD_ACK:
                rtt = self._time_diff(current, ts)
                if rtt >= 0:
                    self._update_rtt(rtt)
                self._parse_ack(sn)
                self._shrink_buf()
            elif cmd == IKCP_CMD_PUSH:
                if self._time_diff(sn, self.rcv_nxt + self.rcv_wnd) < 0:
                    self.acklist.append((sn, ts))
                    if self._time_diff(sn, self.rcv_nxt) >= 0:
                        seg = KCPSegment(conv, cmd, frg, wnd, ts, sn, una, payload)
                        self._parse_data(seg)
        return 0

    def update(self):
        """Timer callback called at fixed interval (e.g., 10ms)"""
        current = self.current_ms()
        if not self.updated:
            self.updated = True
            self.ts_flush = current

        slap = self._time_diff(current, self.ts_flush)
        if slap >= 0 or slap < -10000:
            self.ts_flush = current
            self.flush()

    def flush(self):
        """Flushes ACKs and pending send buffer packets"""
        current = self.current_ms()
        
        # 1. Flush ACKs immediately
        for sn, ts in self.acklist:
            seg = KCPSegment(self.conv, IKCP_CMD_ACK, 0, self._wnd_unused(), ts, sn, self.rcv_nxt)
            self.output(seg.encode())
        self.acklist.clear()
        
        # 2. Move items from send queue to send buffer according to window
        cwnd = min(self.snd_wnd, self.rmt_wnd)
        if not self.nocwnd:
            cwnd = min(self.cwnd, cwnd)
            
        while self._time_diff(self.snd_nxt, self.snd_una + cwnd) < 0 and self.snd_queue:
            newseg = self.snd_queue.popleft()
            newseg.conv = self.conv
            newseg.cmd = IKCP_CMD_PUSH
            newseg.wnd = self._wnd_unused()
            newseg.ts = current
            newseg.sn = self.snd_nxt
            self.snd_nxt = (self.snd_nxt + 1) & 0xFFFFFFFF
            newseg.una = self.rcv_nxt
            newseg.resendts = current
            newseg.rto = self.rx_rto
            newseg.fastack = 0
            newseg.xmit = 0
            self.snd_buf.append(newseg)
            
        # 3. Transmit packets in send buffer
        for seg in self.snd_buf:
            needsend = False
            if seg.xmit == 0:
                needsend = True
                seg.xmit += 1
                seg.rto = self.rx_rto
                seg.resendts = (current + seg.rto + (seg.rto if self.nodelay else 0)) & 0xFFFFFFFF
            elif self._time_diff(current, seg.resendts) >= 0:
                needsend = True
                seg.xmit += 1
                seg.rto += (seg.rto // 2 if self.nodelay else seg.rto)
                seg.resendts = (current + seg.rto) & 0xFFFFFFFF
            elif self.fastresend > 0 and seg.fastack >= self.fastresend:
                needsend = True
                seg.xmit += 1
                seg.fastack = 0
                seg.resendts = (current + seg.rto) & 0xFFFFFFFF
                
            if needsend:
                seg.ts = current
                seg.wnd = self._wnd_unused()
                seg.una = self.rcv_nxt
                self.output(seg.encode())

    def _wnd_unused(self) -> int:
        nrcv = len(self.rcv_queue)
        if nrcv < self.rcv_wnd:
            return self.rcv_wnd - nrcv
        return 0

    def _parse_una(self, una: int):
        # Remove all acknowledged segments with sn < una (bulk filter)
        self.snd_buf = [seg for seg in self.snd_buf if self._time_diff(una, seg.sn) <= 0]

    def _parse_ack(self, sn: int):
        if self._time_diff(sn, self.snd_una) < 0 or self._time_diff(sn, self.snd_nxt) >= 0:
            return
        for idx, seg in enumerate(self.snd_buf):
            if sn == seg.sn:
                self.snd_buf.pop(idx)
                break
            elif self._time_diff(sn, seg.sn) < 0:
                break
            else:
                seg.fastack += 1

    def _shrink_buf(self):
        if self.snd_buf:
            self.snd_una = self.snd_buf[0].sn
        else:
            self.snd_una = self.snd_nxt

    def _parse_data(self, newseg: KCPSegment):
        sn = newseg.sn
        if self._time_diff(sn, self.rcv_nxt + self.rcv_wnd) >= 0 or self._time_diff(sn, self.rcv_nxt) < 0:
            return
        
        # Insert into rcv_buf sorted by sn
        inserted = False
        for idx in range(len(self.rcv_buf) - 1, -1, -1):
            seg = self.rcv_buf[idx]
            if seg.sn == sn:
                return # Duplicate
            if self._time_diff(sn, seg.sn) > 0:
                self.rcv_buf.insert(idx + 1, newseg)
                inserted = True
                break
        if not inserted:
            self.rcv_buf.insert(0, newseg)
            
        # Move continuous packets from rcv_buf to rcv_queue
        while self.rcv_buf and self.rcv_buf[0].sn == self.rcv_nxt:
            seg = self.rcv_buf.pop(0)
            self.rcv_queue.append(seg)
            self.rcv_nxt = (self.rcv_nxt + 1) & 0xFFFFFFFF

    def _update_rtt(self, rtt: int):
        if self.rx_srtt == 0:
            self.rx_srtt = rtt
            self.rx_rttval = rtt // 2
        else:
            delta = abs(rtt - self.rx_srtt)
            self.rx_rttval = (3 * self.rx_rttval + delta) // 4
            self.rx_srtt = (7 * self.rx_srtt + rtt) // 8
            if self.rx_srtt < 1:
                self.rx_srtt = 1
        rto = self.rx_srtt + max(self.interval, 4 * self.rx_rttval)
        self.rx_rto = max(self.rx_minrto, min(rto, 60000))

    @staticmethod
    def _time_diff(later: int, earlier: int) -> int:
        return (later - earlier + 0x80000000) % 0x100000000 - 0x80000000
