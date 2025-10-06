import random
import socket as soc

from constants import *
from Packets import AckPacket, DataPacket, Packet

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1


def udt_rcv(sock: soc.socket) -> bytes:
    return sock.recv(1024)


def udt_send(sock: soc.socket, pkt: bytes):
    sock.sendto(pkt, (RX_ADDR, RX_PORT))


class RDT22Receiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.state = WAIT_0
        self.once = False  # same as oncethru
        self.last_ack: dict[int, AckPacket | None] = {0: None, 1: None}
        self.scenario = scenario
        self.loss_rate = loss_rate

    def get_data_pkt(self) -> DataPacket | None:
        "Called by application to get received data, returns None if data is corrupted"
        rcvpkt = udt_rcv(self.sock)

        rcvpkt = self.__corrupt_data_bytes(rcvpkt)

        if self.state == WAIT_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 0:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(0)
                udt_send(self.sock, ack.extract_data())
                self.last_ack[0] = ack
                self.once = True
                self.state = WAIT_1

                return data
            else:  # corrupt or has_seq1
                if self.once and self.last_ack[0]:
                    udt_send(self.sock, self.last_ack[0].extract_data())

                return None

        elif self.state == WAIT_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 1:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(1)
                udt_send(self.sock, ack.extract_data())
                self.last_ack[1] = ack
                self.state = WAIT_0

                return data
            else:  # corrupt or has_seq0
                if self.last_ack[1]:
                    udt_send(self.sock, self.last_ack[1].extract_data())

                return None

    def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts data packets depending on the scenario and loss rate"""

        if self.scenario == NO_LOSS:
            return rx_bytes
        elif self.scenario == TX_ACK_LOSS:
            return rx_bytes
        elif self.scenario == RX_DATA_LOSS:
            if random.random() < self.loss_rate:
                corrupt_data = random.randint(
                    0, 2 ** (8 * DataPacket.DATA_SIZE) - 1
                )  # random corrupt data packet
                full_corrupt_data = (
                    rx_bytes[0:2]
                    + corrupt_data.to_bytes(DataPacket.DATA_SIZE, "big")
                    + rx_bytes[-2:]
                )
                return full_corrupt_data
            else:
                return rx_bytes
        else:
            raise NotImplementedError
