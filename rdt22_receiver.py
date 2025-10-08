import random
import socket as soc

from constants import *
from Packets import AckPacket, DataPacket, Packet

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1

# remember where the last DATA came from so we can reply ACKs to that address
_last_sender_addr: tuple[str, int] | None = None


def udt_rcv(sock: soc.socket) -> bytes:
    data, addr = sock.recvfrom(2048)  # use recvfrom on UDP
    global _last_sender_addr
    _last_sender_addr = addr
    return data


def udt_send(sock: soc.socket, pkt: bytes):
    # send ACKs back to the most recent sender (not RX_ADDR/RX_PORT)
    if _last_sender_addr is not None:
        sock.sendto(pkt, _last_sender_addr)


class RDT22Receiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.sock = sock
        self.state = WAIT_0
        self.once = False  # same as oncethru
        self.last_ack: dict[int, AckPacket | None] = {0: None, 1: None}
        self.scenario = scenario
        # normalize to 0..1 if 0..100 was passed
        self.loss_rate = loss_rate if 0.0 <= loss_rate <= 1.0 else max(0.0, min(1.0, loss_rate / 100.0))

    def get_data_pkt(self) -> DataPacket | None:
        "Called by application to get received data, returns None if data is corrupted"
        rcvpkt = udt_rcv(self.sock)

        rcvpkt = self.__corrupt_data_bytes(rcvpkt)

        if self.state == WAIT_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 0:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(0)
                udt_send(self.sock, ack.to_bytes())  # was ack.extract_data()
                self.last_ack[0] = ack
                self.once = True
                self.state = WAIT_1

                return data
            else:  # corrupt or has_seq1
                if self.once and self.last_ack[0]:
                    udt_send(self.sock, self.last_ack[0].to_bytes())  # was extract_data()
                return None

        elif self.state == WAIT_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.data_seq(rcvpkt) == 1:
                data = DataPacket.packet_from_bytes(rcvpkt)
                ack = AckPacket(1)
                udt_send(self.sock, ack.to_bytes())  # was ack.extract_data()
                self.last_ack[1] = ack
                self.state = WAIT_0

                return data
            else:  # corrupt or has_seq0
                if self.last_ack[1]:
                    udt_send(self.sock, self.last_ack[1].to_bytes())  # was extract_data()
                return None

def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
                """Randomly corrupts data packets depending on the scenario and loss rate"""
            
                if self.scenario == NO_LOSS:
                    return rx_bytes
                elif self.scenario == TX_ACK_LOSS:
                    return rx_bytes
                elif self.scenario == RX_DATA_LOSS:
                    if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                        # Flip a single bit in the DATA area.
                        # Avoid the 2-byte header [0:2] and the 2-byte checksum [-2:].
                        ba = bytearray(rx_bytes)
                        # pick a middle index within the data/padding region
                        i = max(2, min(len(ba) - 3, 2 + (len(ba) - 4) // 2))
                        ba[i] ^= 0x01
                        return bytes(ba)
                    else:
                        return rx_bytes
                else:
                    raise NotImplementedError
            
