import random
import socket as soc
import time

import constants
from Packets import DataPacket, Packet

# --- State constants ---
WAIT_CALL_0 = 0
WAIT_ACK_0 = 1
WAIT_CALL_1 = 2
WAIT_ACK_1 = 3


def udt_rcv(sock: soc.socket) -> bytes:
    # Use recvfrom on UDP (works without connect())
    data, _ = sock.recvfrom(1024)
    return data


class RDT22Sender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.sock.settimeout(0.01)  # resend if no ACK within 10 ms
        self.state = WAIT_CALL_0
        self.last_pkt: DataPacket | None = None  # buffer last sent packet
        self.scenario = scenario
        # Normalize loss_rate to 0..1 if user passes 0..100
        self.loss_rate = loss_rate if 0.0 <= loss_rate <= 1.0 else max(0.0, min(1.0, loss_rate / 100.0))

    def udt_send(self, sock: soc.socket, pkt: bytes):
        if self.__corrupt_ACK_bytes(pkt) == bytes():
            return
        elif self.scenario == constants.TX_ACK_SLOW:
            time.sleep(1)
        sock.sendto(pkt, (constants.RX_ADDR, constants.RX_PORT))

    def rdt_send(self, curr_packet: DataPacket):
        """Called by application to send one chunk of data"""
        if self.state == WAIT_CALL_0:
            self.last_pkt = curr_packet
            self.udt_send(self.sock, self.last_pkt.full_pkt)
            self.state = WAIT_ACK_0

        elif self.state == WAIT_CALL_1:
            self.last_pkt = curr_packet
            self.udt_send(self.sock, self.last_pkt.full_pkt)
            self.state = WAIT_ACK_1

        else:
            # If app calls at wrong time, ignore or block until ready
            pass

    def input(self) -> bool:
        """Called when a packet arrives from receiver"""
        try:
            rcvpkt = udt_rcv(self.sock)
        except soc.timeout:
            # Treat timeout as lost packet -> resend last packet
            if self.last_pkt is not None:
                self.udt_send(self.sock, self.last_pkt.full_pkt)
            return True

        rcvpkt = self.__corrupt_ACK_bytes(rcvpkt)

        resent = False

        if self.last_pkt is None:
            return resent

        if self.state == WAIT_ACK_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 0:
                self.state = WAIT_CALL_1
            else:  # corrupt or wrong ACK
                self.udt_send(self.sock, self.last_pkt.full_pkt)
                resent = True

        elif self.state == WAIT_ACK_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 1:
                self.state = WAIT_CALL_0
            else:  # corrupt or wrong ACK
                self.udt_send(self.sock, self.last_pkt.full_pkt)
                resent = True

        return resent

    def __corrupt_ACK_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts ACK packets depending on the scenario and loss rate"""

        match self.scenario:
            case constants.NO_LOSS | constants.RX_DATA_LOSS | constants.TX_ACK_DROP | constants.TX_ACK_SLOW | constants.RX_DATA_SLOW:
                return rx_bytes
            case constants.RX_DATA_DROP:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    return bytes()
                else:
                    return rx_bytes
            case constants.TX_ACK_LOSS:
                   # TODO: Why is this >=3....
                if random.random() < self.loss_rate and len(rx_bytes) >= 3:
                    # Flip a single bit in the middle (keeps length; breaks checksum)
                    ba = bytearray(rx_bytes)
                    mid = len(ba) // 2
                    ba[mid] ^= 0x01
                    return bytes(ba)
                else:
                    return rx_bytes
            case _:
                raise NotImplementedError
