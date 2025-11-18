import random
import socket as soc
import time
from datetime import datetime

import constants
from Packets import AckPacket, DataPacket, Packet

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1


class RDT22Receiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.last_sender_addr: tuple[str, int] | None = None
        self.sock = sock
        self.expected_seq: int = 1
        self.sndpkt: AckPacket = AckPacket(0)  # initial ACK for seq 0
        self.scenario = scenario
        # normalize to 0..1 if 0..100 was passed
        self.loss_rate = (
            loss_rate
            if 0.0 <= loss_rate <= 1.0
            else max(0.0, min(1.0, loss_rate / 100.0))
        )

    def udt_rcv(self, sock: soc.socket) -> bytes:
        data, addr = sock.recvfrom(constants.MAX_PACKET_SIZE)  # use recvfrom on UDP
        # remember where the last DATA came from so we can reply ACKs to that address
        self.last_sender_addr = addr
        return data

    def udt_send(self, sock: soc.socket, pkt: bytes):
        # send ACKs back to the most recent sender (not RX_ADDR/RX_PORT)
        if self.last_sender_addr is not None:
            if self.scenario == constants.TX_ACK_SLOW:
                time.sleep(1)
            sock.sendto(pkt, self.last_sender_addr)

    def get_data(self) -> bytes | None:
        "Called by application to get received data, returns None if data is corrupted"
        rcvpkt = self.udt_rcv(self.sock)

        rcvpkt = self.__corrupt_data_bytes(rcvpkt)
        if rcvpkt == bytes():
            return None

        data_pkt = Packet(rcvpkt)

        if data_pkt.is_corrupt():
            print(
                f"[{datetime.now().strftime('%S.%f')}] Packet corrupt. Resending ACK {self.sndpkt.seq_num}"
            )
            self.udt_send(self.sock, self.sndpkt.to_bytes())
            return None

        if data_pkt.seq_num != self.expected_seq:
            print(
                f"[{datetime.now().strftime('%S.%f')}] Got packet # {data_pkt.seq_num}; # {self.expected_seq} was expected. Resending ACK {self.sndpkt.seq_num}"
            )
            self.udt_send(self.sock, self.sndpkt.to_bytes())
            return None
        else:
            print(
                f"[{datetime.now().strftime('%S.%f')}] Good packet. Seq# {data_pkt.seq_num}"
            )

        if not data_pkt.is_corrupt() and data_pkt.seq_num == self.expected_seq:
            self.sndpkt = AckPacket(self.expected_seq)
            self.expected_seq += 1
            self.udt_send(self.sock, self.sndpkt.to_bytes())

            return data_pkt.data

        # If we reach here, either packet is corrupt or unexpected seq num
        # Resend last ACK
        print(
            f"[{datetime.now().strftime('%S.%f')}] Packet corrupt or unexpected, resend ACKfor SeqNum# {self.sndpkt.seq_num}"
        )
        self.udt_send(self.sock, self.sndpkt.to_bytes())
        return None

    def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts data packets depending on the scenario and loss rate"""

        match self.scenario:
            case (
                constants.NO_LOSS
                | constants.TX_ACK_LOSS
                | constants.TX_ACK_SLOW
                | constants.RX_DATA_SLOW
                | constants.TX_ACK_DROP
            ):
                return rx_bytes
            case constants.RX_DATA_DROP:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    print(f"[{datetime.now().strftime('%S.%f')}] Packet dropped")
                    return bytes()
                else:
                    return rx_bytes
            case constants.RX_DATA_LOSS:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    corrupt_data = random.randint(
                        0, 2 ** (8 * constants.MAX_PACKET_SIZE) - 1
                    )  # random corrupt data packet
                    full_corrupt_data = (
                        rx_bytes[0:2]
                        + corrupt_data.to_bytes(constants.MAX_PACKET_SIZE, "big")
                        + rx_bytes[-2:]
                    )
                    return full_corrupt_data
                else:
                    return rx_bytes
            case _:
                raise NotImplementedError
