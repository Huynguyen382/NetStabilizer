"""
Comprehensive Unit tests for Forward Error Correction (FEC) packet loss recovery
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fec import FECEncoder, FECDecoder

class TestFEC(unittest.TestCase):
    def test_fec_loss_recovery_single_packet_binary(self):
        """Simulates dropping 1 binary packet with trailing null bytes and verifies exact reconstruction"""
        encoder = FECEncoder(data_shards=10, parity_shards=3)
        decoder = FECDecoder()

        # Binary data including null bytes and binary control codes (simulating video frame or RDP payload)
        test_data = [
            f"BinaryPacket_{i}".encode("utf-8") + b"\x00\x00\x00\x00\xfe\xff\x00\x00"
            for i in range(10)
        ]
        
        all_transmitted_packets = []
        for pkt in test_data:
            out = encoder.encode_packet(pkt)
            all_transmitted_packets.extend(out)

        # 10 data packets + 3 parity packets = 13 packets
        self.assertEqual(len(all_transmitted_packets), 13)

        # Drop index 4 (5th data packet)
        dropped_idx = 4
        received_by_receiver = [p for i, p in enumerate(all_transmitted_packets) if i != dropped_idx]

        recovered_data = []
        total_recovered_count = 0

        for p in received_by_receiver:
            data_list, rec_cnt = decoder.decode_packet(p)
            recovered_data.extend(data_list)
            total_recovered_count += rec_cnt

        self.assertEqual(len(recovered_data), 10)
        self.assertEqual(total_recovered_count, 1)
        self.assertIn(test_data[dropped_idx], recovered_data)
        self.assertEqual(set(recovered_data), set(test_data))

    def test_fec_two_packet_loss_recovery(self):
        """Tests recovery when 2 packets (one even index, one odd index) are lost simultaneously"""
        encoder = FECEncoder(data_shards=10, parity_shards=3)
        decoder = FECDecoder()

        test_data = [f"PayloadSegment_{i:02d}".encode("utf-8") for i in range(10)]
        
        all_transmitted = []
        for pkt in test_data:
            all_transmitted.extend(encoder.encode_packet(pkt))

        # Drop packet 2 (even) and packet 5 (odd)
        dropped_indices = {2, 5}
        received = [p for i, p in enumerate(all_transmitted) if i not in dropped_indices]

        recovered_data = []
        total_recovered_cnt = 0
        for p in received:
            data_list, rec_cnt = decoder.decode_packet(p)
            recovered_data.extend(data_list)
            total_recovered_cnt += rec_cnt

        self.assertEqual(len(recovered_data), 10)
        self.assertEqual(total_recovered_cnt, 2)
        self.assertIn(test_data[2], recovered_data)
        self.assertIn(test_data[5], recovered_data)
        self.assertEqual(set(recovered_data), set(test_data))

    def test_fec_partial_group_flush(self):
        """Tests that flush() correctly handles partial groups (e.g. 4 packets instead of 10)"""
        encoder = FECEncoder(data_shards=10, parity_shards=3)
        decoder = FECDecoder()

        test_data = [f"Partial_{i}".encode("utf-8") for i in range(4)]
        transmitted = []
        for pkt in test_data:
            transmitted.extend(encoder.encode_packet(pkt))
        
        transmitted.extend(encoder.flush())

        # Drop packet 1
        received = [p for i, p in enumerate(transmitted) if i != 1]
        recovered = []
        for p in received:
            d_list, _ = decoder.decode_packet(p)
            recovered.extend(d_list)

        self.assertEqual(len(recovered), 4)
        self.assertIn(test_data[1], recovered)
        self.assertEqual(set(recovered), set(test_data))

if __name__ == "__main__":
    unittest.main()
