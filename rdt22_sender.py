import random
import socket as soc
from typing import Optional

from constants import *
from Packets import DataPacket, Packet

# --- State constants ---
WAIT_CALL_0 = 0
WAIT_ACK_0 = 1
WAIT_CALL_1 = 2
WAIT_ACK_1 = 3


def udt_rcv(sock: soc.socket) -> bytes:
    # Use recvfrom to avoid connected-UDP ICMP errors
    try:
        data, _ = sock.recvfrom(1024)
        return data
    except ConnectionRefusedError:
        # Treat as a timeout so resend logic kicks in
        raise soc.timeout


def udt_send(sock: soc.socket, pkt: bytes):
    # Send DATA to receiver
    sock.sendto(pkt, (RX_ADDR, RX_PORT))


class RDT22Sender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.sock.settimeout(0.5)  # resend if no ACK within 500 ms
        self.state = WAIT_CALL_0
        self.last_pkt: Optional[DataPacket] = None  # buffer last sent packet
        self.scenario = scenario
        # accept 0–1 or 0–100
        self.loss_rate = (
            loss_rate
            if 0.0 <= loss_rate <= 1.0
            else max(0.0, min(1.0, loss_rate / 100.0))
        )

    def rdt_send(self, curr_packet: DataPacket):
        """Called by application to send one chunk of data."""
        if self.state == WAIT_CALL_0:
            self.last_pkt = curr_packet
            udt_send(self.sock, self.last_pkt.full_pkt)
            self.state = WAIT_ACK_0

        elif self.state == WAIT_CALL_1:
            self.last_pkt = curr_packet
            udt_send(self.sock, self.last_pkt.full_pkt)
            self.state = WAIT_ACK_1

        else:
            # Called while waiting for ACK; ignore (app should call after we move back to WAIT_CALL_x)
            pass

    def input(self) -> bool:
        """Called when an ACK arrives from receiver. Returns True if we had to resend last data."""
        try:
            rcvpkt = udt_rcv(self.sock)
        except soc.timeout:
            if self.last_pkt is not None:
                udt_send(self.sock, self.last_pkt.full_pkt)  # timeout -> resend
                return True
            return False

        rcvpkt = self.__corrupt_ACK_bytes(rcvpkt)

        resent = False
        if self.last_pkt is None:
            return resent

        if self.state == WAIT_ACK_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 0:
                self.state = WAIT_CALL_1
            else:
                # corrupt/wrong ACK -> resend last packet
                udt_send(self.sock, self.last_pkt.full_pkt)
                resent = True

        elif self.state == WAIT_ACK_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 1:
                self.state = WAIT_CALL_0
            else:
                udt_send(self.sock, self.last_pkt.full_pkt)
                resent = True

        return resent

    def __corrupt_ACK_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupt ACK bytes for the TX_ACK_LOSS scenario."""
        if self.scenario == NO_LOSS:
            return rx_bytes

        if self.scenario == TX_ACK_LOSS:
            if random.random() < self.loss_rate and len(rx_bytes) >= 3:
                ba = bytearray(rx_bytes)
                # Flip a bit in a middle byte to force checksum/parse failure
                mid = len(ba) // 2
                ba[mid] ^= 0x01
                return bytes(ba)
            return rx_bytes

        # RX_DATA_LOSS handled on receiver side; ACKs unmodified here
        return rx_bytes
