"""
NetStabilizer - FEC (Forward Error Correction) Module
High-performance packet loss recovery engine utilizing systematic XOR Multi-Parity.
Allows instant zero-RTT recovery of lost packets over unstable Wi-Fi or Internet links.
"""

import struct
import time
from typing import List, Optional, Tuple, Dict

# Header format: Magic(2B) + GroupID(4B) + SeqInGroup(2B) + DataShards(2B) + ParityShards(2B)
# Total header size = 12 bytes
FEC_MAGIC = 0xFEC1
FEC_HEADER_STRUCT = struct.Struct("!HIHHH")
FEC_HEADER_SIZE = FEC_HEADER_STRUCT.size

def _xor_bytes(a: bytearray, b: bytes):
    """Fast in-place XOR of byte sequences using word/integer chunks"""
    len_a = len(a)
    len_b = len(b)
    common_len = min(len_a, len_b)
    
    # Process 8 bytes (64-bit word) at a time for high speed
    word_count = common_len // 8
    if word_count > 0:
        words_end = word_count * 8
        for offset in range(0, words_end, 8):
            w_a = int.from_bytes(a[offset:offset+8], 'little')
            w_b = int.from_bytes(b[offset:offset+8], 'little')
            a[offset:offset+8] = (w_a ^ w_b).to_bytes(8, 'little')
        for i in range(words_end, common_len):
            a[i] ^= b[i]
    else:
        for i in range(common_len):
            a[i] ^= b[i]

class FECEncoder:
    """
    Encodes data packets into FEC groups and generates redundant parity packets.
    """
    def __init__(self, data_shards: int = 10, parity_shards: int = 3):
        self.data_shards = max(1, data_shards)
        self.parity_shards = max(1, min(parity_shards, 3))
        self.current_group_id = 0
        self.buffer: List[bytes] = []

    def encode_packet(self, data: bytes) -> List[bytes]:
        """
        Takes raw payload, packages it with FEC header.
        When a full group (data_shards) is collected, generates parity packets.
        Returns a list of packets ready to send over UDP.
        """
        group_id = self.current_group_id
        seq = len(self.buffer)
        
        # Prefix length (2B) to preserve exact payload size including binary null bytes
        framed_data = struct.pack("!H", len(data)) + data
        self.buffer.append(framed_data)

        # Build data packet with FEC header
        hdr = FEC_HEADER_STRUCT.pack(FEC_MAGIC, group_id, seq, self.data_shards, self.parity_shards)
        out_packets = [hdr + framed_data]

        # Check if group is complete, if so generate parity shards
        if len(self.buffer) >= self.data_shards:
            parity_packets = self._generate_parity(group_id, self.buffer)
            out_packets.extend(parity_packets)
            self.buffer.clear()
            self.current_group_id = (self.current_group_id + 1) & 0xFFFFFFFF

        return out_packets

    def flush(self) -> List[bytes]:
        """Flushes incomplete group if needed"""
        if not self.buffer:
            return []
        group_id = self.current_group_id
        actual_shards = len(self.buffer)
        parity_packets = self._generate_parity(group_id, self.buffer, actual_shards=actual_shards)
        self.buffer.clear()
        self.current_group_id = (self.current_group_id + 1) & 0xFFFFFFFF
        return parity_packets

    def _generate_parity(self, group_id: int, data_packets: List[bytes], actual_shards: Optional[int] = None) -> List[bytes]:
        """Generates multi-parity shards using systematic XOR scheme"""
        if not data_packets:
            return []
        
        d_shards = actual_shards or self.data_shards
        max_len = max(len(p) for p in data_packets)
        
        # P0: XOR of ALL data packets
        p0 = bytearray(max_len)
        for pkt in data_packets:
            _xor_bytes(p0, pkt)

        parity_list = []
        # Parity 0: Global parity
        hdr0 = FEC_HEADER_STRUCT.pack(FEC_MAGIC, group_id, d_shards + 0, d_shards, self.parity_shards)
        parity_list.append(hdr0 + bytes(p0))

        if self.parity_shards >= 2:
            # Parity 1: Even index packets (0, 2, 4, ...)
            p1 = bytearray(max_len)
            for i in range(0, len(data_packets), 2):
                _xor_bytes(p1, data_packets[i])
            hdr1 = FEC_HEADER_STRUCT.pack(FEC_MAGIC, group_id, d_shards + 1, d_shards, self.parity_shards)
            parity_list.append(hdr1 + bytes(p1))

        if self.parity_shards >= 3:
            # Parity 2: Odd index packets (1, 3, 5, ...)
            p2 = bytearray(max_len)
            for i in range(1, len(data_packets), 2):
                _xor_bytes(p2, data_packets[i])
            hdr2 = FEC_HEADER_STRUCT.pack(FEC_MAGIC, group_id, d_shards + 2, d_shards, self.parity_shards)
            parity_list.append(hdr2 + bytes(p2))

        return parity_list


class FECDecoder:
    """
    Decodes received packets, tracks missing packets per group,
    and reconstructs lost data packets immediately upon receiving parity shards.
    """
    def __init__(self, max_groups: int = 128, timeout: float = 2.0):
        self.max_groups = max_groups
        self.timeout = timeout
        self.groups: Dict[int, Dict] = {}

    def decode_packet(self, raw_packet: bytes) -> Tuple[List[bytes], int]:
        """
        Parses incoming UDP packet.
        Returns:
            (list of recovered or passed data packets, number_of_recovered_packets)
        """
        if len(raw_packet) < FEC_HEADER_SIZE:
            return ([raw_packet], 0)

        magic, group_id, seq, data_shards, parity_shards = FEC_HEADER_STRUCT.unpack_from(raw_packet, 0)
        if magic != FEC_MAGIC:
            return ([raw_packet], 0)

        payload = raw_packet[FEC_HEADER_SIZE:]
        now = time.monotonic()
        self._cleanup_old_groups(now)

        if group_id not in self.groups:
            self.groups[group_id] = {
                'created': now,
                'data': {},
                'parity': {},
                'data_shards': data_shards,
                'parity_shards': parity_shards,
                'recovered_seqs': set()
            }

        grp = self.groups[group_id]
        recovered_packets: List[bytes] = []
        num_recovered = 0

        if seq < data_shards:
            # Original data packet
            if seq not in grp['data']:
                grp['data'][seq] = payload
                unframed = self._unframe(payload)
                if unframed is not None:
                    recovered_packets.append(unframed)
        else:
            # Parity packet
            grp['parity'][seq] = payload

        # Check if we can recover any missing packets
        received_data_count = len(grp['data'])
        if received_data_count < data_shards and grp['parity']:
            missing_seqs = [s for s in range(data_shards) if s not in grp['data']]
            
            # Case 1: Single missing packet anywhere in group (recoverable via P0)
            p0_seq = data_shards + 0
            if len(missing_seqs) == 1 and p0_seq in grp['parity'] and missing_seqs[0] not in grp['recovered_seqs']:
                missing_seq = missing_seqs[0]
                reconstructed = self._reconstruct_from_group(grp, missing_seq, grp['parity'][p0_seq], list(grp['data'].keys()))
                if reconstructed:
                    grp['data'][missing_seq] = reconstructed
                    grp['recovered_seqs'].add(missing_seq)
                    unframed = self._unframe(reconstructed)
                    if unframed is not None:
                        recovered_packets.append(unframed)
                        num_recovered += 1

            # Case 2: Two missing packets (one even, one odd) (recoverable via P1 and P2)
            elif len(missing_seqs) == 2:
                m_even = [s for s in missing_seqs if s % 2 == 0]
                m_odd = [s for s in missing_seqs if s % 2 == 1]
                
                p1_seq = data_shards + 1
                p2_seq = data_shards + 2

                if len(m_even) == 1 and p1_seq in grp['parity'] and m_even[0] not in grp['recovered_seqs']:
                    known_evens = [s for s in grp['data'].keys() if s % 2 == 0]
                    rec_even = self._reconstruct_from_group(grp, m_even[0], grp['parity'][p1_seq], known_evens)
                    if rec_even:
                        grp['data'][m_even[0]] = rec_even
                        grp['recovered_seqs'].add(m_even[0])
                        unframed = self._unframe(rec_even)
                        if unframed is not None:
                            recovered_packets.append(unframed)
                            num_recovered += 1

                if len(m_odd) == 1 and p2_seq in grp['parity'] and m_odd[0] not in grp['recovered_seqs']:
                    known_odds = [s for s in grp['data'].keys() if s % 2 == 1]
                    rec_odd = self._reconstruct_from_group(grp, m_odd[0], grp['parity'][p2_seq], known_odds)
                    if rec_odd:
                        grp['data'][m_odd[0]] = rec_odd
                        grp['recovered_seqs'].add(m_odd[0])
                        unframed = self._unframe(rec_odd)
                        if unframed is not None:
                            recovered_packets.append(unframed)
                            num_recovered += 1

        return (recovered_packets, num_recovered)

    def _reconstruct_from_group(self, grp: Dict, missing_seq: int, parity_pkt: bytes, known_seqs: List[int]) -> Optional[bytes]:
        """Reconstructs missing framed data by XORing known shards with parity shard"""
        max_len = len(parity_pkt)
        recon = bytearray(parity_pkt)

        for s in known_seqs:
            if s != missing_seq and s in grp['data']:
                _xor_bytes(recon, grp['data'][s])

        return bytes(recon)

    def _unframe(self, framed_data: bytes) -> Optional[bytes]:
        """Extracts exact original payload using framed length prefix"""
        if len(framed_data) < 2:
            return None
        orig_len = struct.unpack("!H", framed_data[:2])[0]
        return framed_data[2:2 + orig_len]

    def _cleanup_old_groups(self, now: float):
        """Purges expired groups to maintain low memory usage"""
        if len(self.groups) > (self.max_groups // 2):
            expired = [gid for gid, g in self.groups.items() if now - g['created'] > self.timeout]
            for gid in expired:
                del self.groups[gid]
