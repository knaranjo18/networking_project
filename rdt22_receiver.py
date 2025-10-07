import random
import socket as soc
from typing import Optional

from constants import *
from Packets import AckPacket, DataPacket, Packet

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1

# Remember where DATA came from so we can send ACKs back
_last_sender_addr: Optional[tuple[str, int]] = None


def udt_rcv(sock: soc.socket) -> bytes:
    """Receive DATA and remember sender addr for ACKs."""
    global _last_sender_addr
    data, addr = sock.recvfrom(2048)
    _last_sender_addr = addr
    return data


def udt_send(sock: soc.socket, pkt: bytes):
    """Send ACKs back to the most recent sender of DATA."""
    if _last_sender_addr is not None:
        sock.sendto(pkt, _last_sender_addr)


def is_corrupt(pkt: bytes) -> bool:
    return Packet.is_corrupt(pkt)


def has_seq(pkt: bytes, seq: int) -> bool:
    return Packet.data_seq(pkt) == seq


def extract_data(pkt: bytes) -> bytes:
    """Extract payload bytes (Packet.extract_data is a static method)."""
    return Packet.extract_data(pkt)


def make_ack(seq: int) -> bytes:
    """Build an ACK packet for the given sequence."""
    if hasattr(Packet, "make_ack"):
        return Packet.make_ack(seq)
    if hasattr(AckPacket, "for_seq"):
        return AckPacket.for_seq(seq).to_bytes()
    return AckPacket(seq).to_bytes()


class RDT22Receiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.state = WAIT_0
        self.once = False
        self.last_ack: dict[int, Optional[bytes]] = {0: None, 1: None}
        self.scenario = scenario
        self.loss_rate = loss_rate if 0.0 <= loss_rate <= 1.0 else max(0.0, min(1.0, loss_rate / 100.0))

    def get_data_pkt(self) -> Optional[DataPacket]:
        """
        Called by application to get received data.
        Returns a DataPacket or None if the received packet was corrupt/out-of-order.
        """
        rcvpkt = udt_rcv(self.sock)
        rcvpkt = self.__corrupt_data_bytes(rcvpkt)

        if self.state == WAIT_0:
            if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 0):
                payload = extract_data(rcvpkt)
                ack = make_ack(0)
                udt_send(self.sock, ack)
                self.last_ack[0] = ack
                self.once = True
                self.state = WAIT_1
                return DataPacket(payload, 0)
            else:
                if self.once and self.last_ack[0]:
                    udt_send(self.sock, self.last_ack[0])
                return None

        elif self.state == WAIT_1:
            if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 1):
                payload = extract_data(rcvpkt)
                ack = make_ack(1)
                udt_send(self.sock, ack)
                self.last_ack[1] = ack
                self.state = WAIT_0
                return DataPacket(payload, 1)
            else:
                if self.last_ack[1]:
                    udt_send(self.sock, self.last_ack[1])
                return None

    def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupt DATA depending on scenario/loss_rate (bit flip keeps length)."""
        if self.scenario in (NO_LOSS, TX_ACK_LOSS):
            return rx_bytes
        if self.scenario == RX_DATA_LOSS and random.random() < self.loss_rate and len(rx_bytes) >= 3:
            ba = bytearray(rx_bytes)
            mid = len(ba) // 2
            ba[mid] ^= 0x01
            return bytes(ba)
        return rx_bytes
