from dataclasses import dataclass, field

from checksum import check_checksum16, gen_checksum16


@dataclass(frozen=True)
class Packet:
    seq_num: int  # Either 0 or 1
    # 1 byte sequence number (using a full byte to get 2 bytes of data to XOR over), 1 byte ACK, 2 bytes checksum
    # 1st bit of first byte is seq number, rest of first 2 bytes is # of data bytes + variable data length + optional padding + 2 bytes checksum
    full_pkt: bytes = field(
        init=False
    )  # subclasses set this; base provides static helpers

    # Check for data length/ack here too - Jesse
    @staticmethod
    def is_corrupt(pkt: bytes) -> bool:
        if len(pkt) <= 2:
            return True
        # Last two bytes are the checksum
        checksum = pkt[-2:]
        return not check_checksum16(pkt[0:-2], checksum)

    # Not sure if this is right - Jesse
    @staticmethod
    def is_ack(pkt: bytes) -> bool:
        return len(pkt) == 4 and pkt[1] == 0xAA

    @staticmethod
    def is_data(pkt: bytes) -> bool:
        return not Packet.is_ack(pkt)

    @staticmethod
    def ack_seq(pkt: bytes) -> int:
        if not Packet.is_ack(pkt):
            return -1
        return pkt[0]

    @staticmethod
    def data_seq(pkt: bytes) -> int:
        if not Packet.is_data(pkt) or len(pkt) < 2:
            return -1
        header = int.from_bytes(pkt[0:2], "big")
        return (header >> 15) & 0x1  # top bit

    @staticmethod
    def extract_data(pkt: bytes) -> bytes:
        """
        Extract payload from a DATA packet:
        header (2 bytes: [seq|num_data15]) + payload(num_data) + padding + checksum(2)
        """
        if not Packet.is_data(pkt) or len(pkt) < 4:
            return b""
        header = int.from_bytes(pkt[0:2], "big")
        num_data = header & DataPacket.NUM_DATA_ACCESS_MASK
        # Defensive clamp in case of weird inputs
        max_payload = max(0, len(pkt) - 4)
        num_data = min(num_data, max_payload)
        return pkt[2 : 2 + num_data]

    @staticmethod
    def make_ack(seq: int) -> bytes:
        return AckPacket(seq).to_bytes()

    def get_seq(self) -> int:
        return self.seq_num


@dataclass(frozen=True)
class DataPacket(Packet):
    seq_num: int  # 0 or 1
    data: bytes  # actual data
    checksum: bytes  # checksum covers the header and the data

    NUM_DATA_ACCESS_MASK: int = field(
        default=0x7FFF, init=False
    )  # Used for access num data value from first two bytes (can also be used to clear seq_num bit)
    SEQ_NUM_ACCESS_MASK: int = field(
        default=1 << 15, init=False
    )  # Used for accessing seq_num from first two bytes
    FULL_SIZE: int = field(default=1024, init=False)
    HEADER_LENGTH: int = field(default=2, init=False)
    CHECKSUM_LENGTH: int = field(default=2, init=False)
    DATA_SIZE: int = field(default=1024 - 2 - 2, init=False)

    def __init__(self, data: bytes, seq_num: int):
        object.__setattr__(self, "seq_num", seq_num)
        object.__setattr__(self, "data", data)

        # In bytes
        num_data = len(self.data)

        # Clear the leftmost bit of the two bytes
        header = num_data & self.NUM_DATA_ACCESS_MASK

        # Set the left most bit to the sequence number
        header |= seq_num << 15

        header_bytes = header.to_bytes(2, "big")

        if num_data > self.DATA_SIZE:
            raise ValueError(
                f"Data too large ({num_data} bytes). Cannot exceed {self.DATA_SIZE} bytes"
            )

        padding = bytes(
            self.FULL_SIZE - num_data - self.HEADER_LENGTH - self.CHECKSUM_LENGTH
        )

        # The data that the checksum will be calculated over
        sumless_pkt = header_bytes + data + padding

        checksum = gen_checksum16(sumless_pkt)

        object.__setattr__(self, "full_pkt", sumless_pkt + checksum)

    @staticmethod
    def packet_from_bytes(in_bytes: bytes):
        header = int.from_bytes(in_bytes[0:2], "big")

        # Grab the leftmost bit of the header for the sequence number
        seq_num = (header & DataPacket.SEQ_NUM_ACCESS_MASK) >> 15

        # Grab the remaining 15 bits of the header as the number of data bytes
        num_data = header & DataPacket.NUM_DATA_ACCESS_MASK

        data = in_bytes[2 : 2 + num_data]

        # Last two bytes are the checksum
        checksum = in_bytes[-2:]

        valid_pkt = check_checksum16(in_bytes[0:-2], checksum)

        if valid_pkt:
            return DataPacket(data, seq_num)
        else:
            print("Checksum detected error!!!")
            return None


@dataclass(frozen=True)
class AckPacket(Packet):
    ack_msg: bytes = field(default=bytes([0xAA]), init=False)
    full_pkt: bytes = field(
        init=False
    )  # 1 byte sequence number (using a full byte to get 2 bytes of data to XOR over), 1 byte ACK, 2 bytes checksum

    FULL_SIZE: int = field(default=4, init=False)
    CHECKSUM_LENGTH: int = field(default=2, init=False)
    HEADER_LENGTH: int = field(default=1, init=False)
    ACK_LENGTH: int = field(default=1, init=False)

    def __init__(self, seq_num: int):
        object.__setattr__(self, "seq_num", seq_num)

        header = seq_num.to_bytes(1, "big")

        # The data that the checksum will be calculated over
        sumless_pkt = header + self.ack_msg

        checksum = gen_checksum16(sumless_pkt)

        object.__setattr__(self, "full_pkt", sumless_pkt + checksum)

    @staticmethod
    def packet_from_bytes(in_bytes: bytes):
        # First byte is the sequence number
        seq_num = int.from_bytes(in_bytes[0:1], "big")

        # Last two bytes are the checksum
        checksum = in_bytes[-2:]

        valid_pkt = check_checksum16(in_bytes[0:-2], checksum)

        if valid_pkt:
            return AckPacket(seq_num)
        else:
            print("Checksum detected error!!!")
            return None

    # Convenience to get raw bytes from an AckPacket instance
    def to_bytes(self) -> bytes:
        return self.full_pkt
