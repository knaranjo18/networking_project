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


TIMEOUT = 0.01


def udt_rcv(sock: soc.socket) -> bytes:
    # Use recvfrom on UDP (works without connect())
    data, _ = sock.recvfrom(constants.MAX_PACKET_SIZE)
    return data


class RDT22Sender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.tot_pkt = 0
        self.num_pkt_affected = 0
        self.sock = sock
        self.sock.settimeout(TIMEOUT)  # resend if no ACK within 10 ms
        self.sndpkt: List[DataPacket] = [
            DataPacket(b"", 1)
        ] * constants.WINDOW_SIZE  # buffer last sent packet
        self.scenario = scenario
        self.base = 1
        self.nextseqnum = 1
        # Normalize loss_rate to 0..1 if user passes 0..100
        self.loss_rate = (
            loss_rate
            if 0.0 <= loss_rate <= 1.0
            else max(0.0, min(1.0, loss_rate / 100.0))
        )

    def udt_send(self, sock: soc.socket, pkt: bytes):
        if self.scenario == constants.TX_ACK_SLOW:
            time.sleep(1)
        sock.sendto(pkt, (constants.RX_ADDR, constants.RX_PORT))

    def rdt_send(self, curr_packet: DataPacket):
        """Called by application to send one chunk of data"""
        if self.nextseqnum < self.base + constants.WINDOW_SIZE:
            self.sndpkt[self.nextseqnum % constants.WINDOW_SIZE] = curr_packet
            self.udt_send(self.sock, curr_packet.to_bytes())
            if self.base == self.nextseqnum:
                pass  # start timer handed by input()
            self.nextseqnum += 1
        else:
            pass

    def do_resend(self) -> None:
        """Resend all packets in the window starting from base to nextseqnum-1"""
        for seq in range(self.base, self.nextseqnum):
            pkt = self.sndpkt[seq % constants.WINDOW_SIZE]
            self.udt_send(self.sock, pkt.to_bytes())

    def input(self) -> bool:
        """Called when a packet arrives from receiver"""

        if len(self.sndpkt) == 0:
            return False

        try:
            rcvpkt = udt_rcv(self.sock)
        except soc.timeout:
            # Resend all packets in the window on timeout
            self.do_resend()
            # restart timer same as just waiting again
            return True

        rcvpkt = self.__corrupt_ACK_bytes(rcvpkt)
        ackpkt = Packet(rcvpkt)
        if not ackpkt.is_corrupt():
            # Theoretically we can make the sequence number go backwards
            self.base = ackpkt.seq_num + 1
            if self.base == self.nextseqnum:
                pass  # stop timer we don't need to stop waiting as
            # we will only call the receive function when we need to get an ACK
            else:
                pass  # restart timer same as just waiting again
        else:  # corrupt ACK
            pass  # do nothing if corrupt

        return False

    def __corrupt_ACK_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts ACK packets depending on the scenario and loss rate"""

        self.tot_pkt += 1

        match self.scenario:
            case (
                constants.NO_LOSS
                | constants.RX_DATA_LOSS
                | constants.TX_ACK_SLOW
                | constants.RX_DATA_SLOW
                | constants.RX_DATA_DROP
            ):
                return rx_bytes
            case constants.TX_ACK_DROP:
                x = random.random()
                if x < self.loss_rate and len(rx_bytes) == 4:
                    self.num_pkt_affected += 1
                    return bytes()
                else:
                    return rx_bytes
            case constants.TX_ACK_LOSS:
                if random.random() < self.loss_rate and len(rx_bytes) >= 4:
                    # Flip a single bit in the middle (keeps length; breaks checksum)
                    ba = bytearray(rx_bytes)
                    mid = len(ba) // 2
                    ba[mid] ^= 0x01
                    return bytes(ba)
                else:
                    return rx_bytes
            case _:
                raise NotImplementedError
