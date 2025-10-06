import random
import socket as soc

from constants import *
from Packets import DataPacket, Packet

# --- State constants ---
WAIT_CALL_0 = 0
WAIT_ACK_0 = 1
WAIT_CALL_1 = 2
WAIT_ACK_1 = 3


def udt_rcv(sock: soc.socket) -> bytes:
    return sock.recv(1024)


def udt_send(sock: soc.socket, pkt: bytes):
    sock.sendto(pkt, (RX_ADDR, RX_PORT))


class RDT22Sender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.state = WAIT_CALL_0
        self.last_pkt: DataPacket | None = None  # buffer last sent packet
        self.scenario = scenario
        self.loss_rate = loss_rate

    def rdt_send(self, curr_packet: DataPacket):
        """Called by application to send one chunk of data"""
        if self.state == WAIT_CALL_0:
            self.last_pkt = curr_packet
            udt_send(self.sock, self.last_pkt.extract_data())
            self.statestate = WAIT_ACK_0

        elif self.state == WAIT_CALL_1:
            self.last_pkt = curr_packet
            udt_send(self.sock, self.last_pkt.extract_data())
            self.state = WAIT_ACK_1
        else:
            # If app calls at wrong time, ignore or block until ready
            pass

    def input(self) -> bool:
        """Called when a packet arrives from receiver"""
        rcvpkt = udt_rcv(self.sock)

        rcvpkt = self.__corrupt_ACK_bytes(rcvpkt)

        resent = False

        if self.last_pkt is None:
            return resent

        if self.state == WAIT_ACK_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 0:
                self.state = WAIT_CALL_1
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.last_pkt.extract_data())
                resent = True

        elif self.state == WAIT_ACK_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 1:
                self.state = WAIT_CALL_0
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.last_pkt.extract_data())
                resent = True

        return resent

    def __corrupt_ACK_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts ACK packets depending on the scenario and loss rate"""

        if self.scenario == NO_LOSS:
            return rx_bytes
        elif self.scenario == TX_ACK_LOSS:
            if random.random() < self.loss_rate:
                corrupt_data = random.randint(0, 255)
                if corrupt_data == 0xAA:
                    corrupt_data += 1
                full_corrupt_ACK = (
                    bytes(rx_bytes[0]) + bytes([corrupt_data]) + rx_bytes[-2:]
                )
                return full_corrupt_ACK
            else:
                return rx_bytes
        elif self.scenario == RX_DATA_LOSS:
            return rx_bytes
        else:
            raise NotImplementedError
