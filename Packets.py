from dataclasses import dataclass, field

from checksum import check_checksum16, gen_checksum16


@dataclass(frozen=True)
class Packet:
    SRC_PORT: int = field(default=0, init=False)
    SRC_PORT_LEN: int = field(default=2, init=False)
    SRC_PORT_MASK: int = field(default=0xFFFF, init=False)
    DST_PORT: int = field(default=2, init=False)
    DST_PORT_LEN: int = field(default=2, init=False)
    DST_PORT_MASK: int = field(default=0xFFFF, init=False)
    SEQ_NUM: int = field(default=4, init=False)
    SEQ_NUM_LEN: int = field(default=4, init=False)
    SEQ_NUM_MASK: int = field(default=0xFFFFFFFF, init=False)
    ACK_NUM: int = field(default=8, init=False)
    ACK_NUM_LEN: int = field(default=4, init=False)
    ACK_NUM_MASK: int = field(default=0xFFFFFFFF, init=False)
    DATA_OFFSET: int = field(default=12, init=False)
    DATA_OFFSET_LEN: int = field(default=1, init=False)
    DATA_OFFSET_MASK: int = field(default=0xF0, init=False)
    FLAGS: int = field(default=13, init=False)
    FLAGS_LEN: int = field(default=1, init=False)
    FLAGS_MASK: int = field(default=0xFF, init=False)
    WINDOW_SIZE: int = field(default=14, init=False)
    WINDOW_SIZE_LEN: int = field(default=2, init=False)
    WINDOW_SIZE_MASK: int = field(default=0xFFFF, init=False)
    CHECKSUM: int = field(default=16, init=False)
    CHECKSUM_LEN: int = field(default=2, init=False)
    CHECKSUM_MASK: int = field(default=0xFFFF, init=False)
    URGENT_POINTER: int = field(default=18, init=False)
    URGENT_POINTER_LEN: int = field(default=2, init=False)
    URGENT_POINTER_MASK: int = field(default=0xFFFF, init=False)

    FLAG_CWR: int = field(default=0x80, init=False)
    FLAG_ECE: int = field(default=0x40, init=False)
    FLAG_URG: int = field(default=0x20, init=False)
    FLAG_ACK: int = field(default=0x10, init=False)
    FLAG_PSH: int = field(default=0x08, init=False)
    FLAG_RST: int = field(default=0x04, init=False)
    FLAG_SYN: int = field(default=0x02, init=False)
    FLAG_FIN: int = field(default=0x01, init=False)

    src_port: int  # source port
    dst_port: int  # destination port
    seq_num: int  # sequence number of the packet
    ack_num: int  # acknowledgment number of the packet
    data_offset: int  # data offset
    cwr: bool  # Congestion Window Reduced flag
    ece: bool  # ECN-Echo flag
    urg: bool  # Urgent flag
    ack: bool  # Acknowledgment flag
    psh: bool  # Push flag
    rst: bool  # Reset flag
    syn: bool  # Synchronize flag
    fin: bool  # Finish flag
    window_size: int  # window size
    checksum: int  # checksum of the packet
    urgent_pointer: int  # urgent pointer
    data: bytes  # payload data

    def __init__(self, raw_data: bytes):
        src_port = int.from_bytes(
            raw_data[self.SRC_PORT : self.SRC_PORT + self.SRC_PORT_LEN], "big"
        )
        object.__setattr__(self, "src_port", src_port & self.SRC_PORT_MASK)
        dst_port = int.from_bytes(
            raw_data[self.DST_PORT : self.DST_PORT + self.DST_PORT_LEN], "big"
        )
        object.__setattr__(self, "dst_port", dst_port & self.DST_PORT_MASK)
        seq_num = int.from_bytes(
            raw_data[self.SEQ_NUM : self.SEQ_NUM + self.SEQ_NUM_LEN], "big"
        )
        object.__setattr__(self, "seq_num", seq_num & self.SEQ_NUM_MASK)
        ack_num = int.from_bytes(
            raw_data[self.ACK_NUM : self.ACK_NUM + self.ACK_NUM_LEN], "big"
        )
        object.__setattr__(self, "ack_num", ack_num & self.ACK_NUM_MASK)
        data_offset = raw_data[self.DATA_OFFSET]
        object.__setattr__(
            self, "data_offset", (data_offset & self.DATA_OFFSET_MASK) >> 4
        )
        flags = raw_data[self.FLAGS]
        object.__setattr__(self, "cwr", bool(flags & self.FLAG_CWR))
        object.__setattr__(self, "ece", bool(flags & self.FLAG_ECE))
        object.__setattr__(self, "urg", bool(flags & self.FLAG_URG))
        object.__setattr__(self, "ack", bool(flags & self.FLAG_ACK))
        object.__setattr__(self, "psh", bool(flags & self.FLAG_PSH))
        object.__setattr__(self, "rst", bool(flags & self.FLAG_RST))
        object.__setattr__(self, "syn", bool(flags & self.FLAG_SYN))
        object.__setattr__(self, "fin", bool(flags & self.FLAG_FIN))
        window_size = int.from_bytes(
            raw_data[self.WINDOW_SIZE : self.WINDOW_SIZE + self.WINDOW_SIZE_LEN], "big"
        )
        object.__setattr__(self, "window_size", window_size & self.WINDOW_SIZE_MASK)
        checksum = int.from_bytes(
            raw_data[self.CHECKSUM : self.CHECKSUM + self.CHECKSUM_LEN], "big"
        )
        object.__setattr__(self, "checksum", checksum & self.CHECKSUM_MASK)
        urgent_pointer = int.from_bytes(
            raw_data[
                self.URGENT_POINTER : self.URGENT_POINTER + self.URGENT_POINTER_LEN
            ],
            "big",
        )
        object.__setattr__(
            self, "urgent_pointer", urgent_pointer & self.URGENT_POINTER_MASK
        )

        object.__setattr__(self, "data", raw_data[self.data_offset * 4 :])

    def to_bytes(self) -> bytes:
        parts: list[bytes] = []
        parts.append(self.src_port.to_bytes(self.SRC_PORT_LEN, "big"))
        parts.append(self.dst_port.to_bytes(self.DST_PORT_LEN, "big"))
        parts.append(self.seq_num.to_bytes(self.SEQ_NUM_LEN, "big"))
        parts.append(self.ack_num.to_bytes(self.ACK_NUM_LEN, "big"))
        data_offset_byte = (self.data_offset << 4) & self.DATA_OFFSET_MASK
        parts.append(data_offset_byte.to_bytes(self.DATA_OFFSET_LEN, "big"))
        flags_byte = 0
        if self.cwr:
            flags_byte |= self.FLAG_CWR
        if self.ece:
            flags_byte |= self.FLAG_ECE
        if self.urg:
            flags_byte |= self.FLAG_URG
        if self.ack:
            flags_byte |= self.FLAG_ACK
        if self.psh:
            flags_byte |= self.FLAG_PSH
        if self.rst:
            flags_byte |= self.FLAG_RST
        if self.syn:
            flags_byte |= self.FLAG_SYN
        if self.fin:
            flags_byte |= self.FLAG_FIN
        parts.append(flags_byte.to_bytes(self.FLAGS_LEN, "big"))
        parts.append(self.window_size.to_bytes(self.WINDOW_SIZE_LEN, "big"))
        parts.append(self.checksum.to_bytes(self.CHECKSUM_LEN, "big"))
        parts.append(self.urgent_pointer.to_bytes(self.URGENT_POINTER_LEN, "big"))
        parts.append(b"\x00" * ((self.data_offset - 5) * 4))
        parts.append(self.data)
        return b"".join(parts)

    def compute_checksum(self) -> int:
        pkt_bytes = self.to_bytes()
        return gen_checksum16(pkt_bytes)

    def is_corrupt(self) -> bool:
        pkt_bytes = self.to_bytes()
        return gen_checksum16(pkt_bytes) != 0

    def is_valid(self) -> bool:
        if self.is_corrupt():
            return False
        if self.data_offset < 5:
            return False
        return True


@dataclass(frozen=True)
class DataPacket(Packet):
    def __init__(self, data: bytes, seq_num: int):
        object.__setattr__(self, "src_port", 0)
        object.__setattr__(self, "dst_port", 0)
        object.__setattr__(self, "seq_num", seq_num)
        object.__setattr__(self, "ack_num", 0)
        object.__setattr__(self, "data_offset", 5)  # assuming no options
        object.__setattr__(self, "cwr", False)
        object.__setattr__(self, "ece", False)
        object.__setattr__(self, "urg", False)
        object.__setattr__(self, "ack", False)
        object.__setattr__(self, "psh", False)
        object.__setattr__(self, "rst", False)
        object.__setattr__(self, "syn", False)
        object.__setattr__(self, "fin", False)
        object.__setattr__(self, "window_size", 0)
        object.__setattr__(self, "checksum", 0)  # will be calculated later
        object.__setattr__(self, "urgent_pointer", 0)
        object.__setattr__(self, "data", data)

        object.__setattr__(self, "checksum", self.compute_checksum())


@dataclass(frozen=True)
class AckPacket(Packet):
    def __init__(self, seq_num: int):
        object.__setattr__(self, "src_port", 0)
        object.__setattr__(self, "dst_port", 0)
        object.__setattr__(self, "seq_num", seq_num)
        object.__setattr__(self, "ack_num", 0)
        object.__setattr__(self, "data_offset", 5)  # assuming no options
        object.__setattr__(self, "cwr", False)
        object.__setattr__(self, "ece", False)
        object.__setattr__(self, "urg", False)
        object.__setattr__(self, "ack", True)
        object.__setattr__(self, "psh", False)
        object.__setattr__(self, "rst", False)
        object.__setattr__(self, "syn", False)
        object.__setattr__(self, "fin", False)
        object.__setattr__(self, "window_size", 0)
        object.__setattr__(self, "checksum", 0)  # will be calculated later
        object.__setattr__(self, "urgent_pointer", 0)
        object.__setattr__(self, "data", b"")

        object.__setattr__(self, "checksum", self.compute_checksum())
