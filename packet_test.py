from Packets import AckPacket, DataPacket

for orig_seq in [0, 1]:
    orig_data = bytes([0xDE, 0xAD, 0xBE, 0xAF])

    orig_datapacket = DataPacket(orig_data, orig_seq)
    orig_datapacket_bytes = orig_datapacket.full_pkt

    rx_datapacket = DataPacket.packet_from_bytes(orig_datapacket_bytes)

    if rx_datapacket:
        rx_seq_num = rx_datapacket.seq_num
        rx_data = rx_datapacket.data
        print("[Pass] Checksum did not detect errors in Data Packet")
    else:
        print("[Fail] Checksum detected errors ni Data Packet")
        exit

    if orig_data == rx_data:
        print("[Pass] Tx matches Rx data")
    else:
        print("[Fail] Tx does not match Rx data")

    if rx_seq_num == orig_seq:
        print(f"[Pass] Sequence numbers match in Data Packet {orig_seq}")
    else:
        print(f"[Fail] Sequence numbers do not match in Data Packet {orig_seq}")

print("")

for orig_ack_seq in [0, 1]:
    ack = AckPacket(orig_ack_seq)
    ack_bytes = ack.full_pkt

    rx_ack = AckPacket.packet_from_bytes(ack_bytes)

    if rx_ack:
        rx_ack0_seq = rx_ack.seq_num
        print("[Pass] Checksum did not detect errors in ACK Packet")
    else:
        print("[Fail] Checksum detected errors in ACK Packet")

    if rx_ack0_seq == orig_ack_seq:
        print(f"[Pass] Sequence numbers match in ACK Packet {orig_ack_seq}")
    else:
        print(f"[Fail] Sequence numbers do not match in ACK Packet {orig_ack_seq}")