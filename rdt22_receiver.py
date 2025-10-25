import random
import socket as soc
import time

import constants
from Packets import AckPacket, DataPacket, Packet

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1


class RDT22Receiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.last_sender_addr: tuple[str, int] | None = None
        self.sock = sock
        self.state = WAIT_0
        self.once = False  # same as oncethru
        self.last_ack: AckPacket
        self.scenario = scenario
        # normalize to 0..1 if 0..100 was passed
        self.loss_rate = loss_rate if 0.0 <= loss_rate <= 1.0 else max(0.0, min(1.0, loss_rate / 100.0))

    def udt_rcv(self, sock: soc.socket) -> bytes:
        data, addr = sock.recvfrom(2048)  # use recvfrom on UDP
        # remember where the last DATA came from so we can reply ACKs to that address
        self.last_sender_addr = addr
        return data

    def udt_send(self, sock: soc.socket, pkt: bytes):
        # send ACKs back to the most recent sender (not RX_ADDR/RX_PORT)
        if self.last_sender_addr is not None:
            if self.scenario == constants.TX_ACK_SLOW:
                time.sleep(1)
            sock.sendto(pkt, self.last_sender_addr)

    def get_data_pkt(self) -> DataPacket | None:
        "Called by application to get received data, returns None if data is corrupted"
        rcvpkt = self.udt_rcv(self.sock)

        rcvpkt = self.__corrupt_data_bytes(rcvpkt)

        if self.state == WAIT_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 0:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(0)
                self.udt_send(self.sock, ack.to_bytes())  # was ack.extract_data()
                self.last_ack = ack
                self.once = True
                self.state = WAIT_1

                return data
            else:  # corrupt or has_seq1
                if rcvpkt == bytes():
                    return None
                elif self.once and self.last_ack:
                    self.udt_send(self.sock, self.last_ack.to_bytes())  # was extract_data()
                else:
                    fake_ack = AckPacket(1)
                    self.udt_send(self.sock, fake_ack.to_bytes())
                return None

        elif self.state == WAIT_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 1:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(1)
                self.udt_send(self.sock, ack.to_bytes())  # was ack.extract_data()
                self.last_ack = ack
                self.state = WAIT_0

                return data
            else:  # corrupt or has_seq0
                if rcvpkt == bytes():
                    return None
                elif self.last_ack:
                    self.udt_send(self.sock, self.last_ack.to_bytes())  # was extract_data()
                else:
                    fake_ack = AckPacket(0)
                    self.udt_send(self.sock, fake_ack.to_bytes())
                return None

    def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts data packets depending on the scenario and loss rate"""

        match self.scenario:
            case constants.NO_LOSS | constants.TX_ACK_LOSS | constants.TX_ACK_SLOW | constants.RX_DATA_SLOW | constants.TX_ACK_DROP:
                return rx_bytes
            case constants.RX_DATA_DROP:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    return bytes()
                else:
                    return rx_bytes
            case constants.RX_DATA_LOSS:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    corrupt_data = random.randint(0, 2 ** (8 * DataPacket.DATA_SIZE) - 1)  # random corrupt data packet
                    full_corrupt_data = rx_bytes[0:2] + corrupt_data.to_bytes(DataPacket.DATA_SIZE, "big") + rx_bytes[-2:]
                    return full_corrupt_data
                else:
                    return rx_bytes
            case _:
                raise NotImplementedError
