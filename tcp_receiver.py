import random
import socket as soc
import time
from datetime import datetime

import constants
from Packets import AckPacket, Packet, SynAcKPacket, FinAckPacket

class TCPReceiver:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float):
        self.last_sender_addr: tuple[str, int] | None = None
        self.sock = sock
        self.expected_seq: int = 1
        self.sndpkt: AckPacket = AckPacket(0, constants.RX_PORT, constants.TX_PORT)  # initial ACK for seq 0
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

            if not self.__drop_ACK_packet():
                sock.sendto(pkt, self.last_sender_addr)


    def establish_connection(self):
        syn_received = False
        ack_received = False

        while not syn_received:
            rcvpkt_bytes = self.udt_rcv(self.sock)
            syn_pkt = Packet(rcvpkt_bytes)
            print(syn_pkt.is_corrupt(), syn_pkt.syn)

            if not syn_pkt.is_corrupt() and syn_pkt.syn:
                if constants.DEBUG_PRINT:
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Good SYN received. Sending SYNACK"
                    )       
                syn_received = True
            else:
                if constants.DEBUG_PRINT:
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Bad SYN received."
                    )   

        while not ack_received:
            synack_pkt = SynAcKPacket(seq_num=0, ack_num=syn_pkt.seq_num+1, src_port=constants.RX_PORT, dst_port=constants.TX_PORT)
            self.udt_send(self.sock, synack_pkt.to_bytes())
        
            rcvpkt_bytes_2 = self.udt_rcv(self.sock)
            ack_pkt = Packet(rcvpkt_bytes_2)

            if not ack_pkt.is_corrupt() and ack_pkt.ack:
                ack_received = True

                if constants.DEBUG_PRINT:
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Final ACK received. Connection established."
                    )                  
            else:
                if constants.DEBUG_PRINT:
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Bad ACK received."
                    )       


    def get_data(self) -> bytes | None:
        "Called by application to get received data, returns None if data is corrupted and -1 if connection done"
        
        # Receive packet and potentially corrupt it
        rcvpkt_bytes = self.udt_rcv(self.sock)
        rcvpkt_bytes = self.__corrupt_data_bytes(rcvpkt_bytes)

        data_pkt = Packet(rcvpkt_bytes)

        # Bad packet - corrupt (resend ACK for previous succesfully received packet)
        if data_pkt.is_corrupt():
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Packet corrupt. Resending ACK # {self.sndpkt.ack_num}"
                )
            self.udt_send(self.sock, self.sndpkt.to_bytes())
            return None

        # Bad packet - out of order (resend ACK for previous succesfully received packet)
        if data_pkt.seq_num != self.expected_seq:
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Got packet # {data_pkt.seq_num}; # {self.expected_seq} was expected. Resending ACK # {self.sndpkt.ack_num}"
                )
            self.udt_send(self.sock, self.sndpkt.to_bytes())
            return None

        # Good packet
        if not data_pkt.is_corrupt() and data_pkt.seq_num == self.expected_seq:
            
            # End connection
            if data_pkt.fin:
                if constants.DEBUG_PRINT:
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Received FIN Packet. Sending FINACK. Closing connection"
                    )
                fin_ack = FinAckPacket(0, data_pkt.dst_port, data_pkt.src_port)
                self.udt_send(self.sock, fin_ack.to_bytes())
                return -1


            self.expected_seq += data_pkt.data_len
            self.sndpkt = AckPacket(self.expected_seq, data_pkt.dst_port, data_pkt.src_port)

            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Good packet of {data_pkt.data_len} bytes. Sending ACK expecting next Seq# {self.expected_seq}"
                )

            self.udt_send(self.sock, self.sndpkt.to_bytes())

            return data_pkt.data


    def __drop_ACK_packet(self) -> bool:
        dropPacket = False
        if self.scenario == constants.TX_ACK_DROP:
            x = random.random()
            if x < self.loss_rate:
                if constants.DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] Dropped ACK Packet")
                dropPacket = True

        return dropPacket
            
    def __corrupt_data_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts data packets depending on the scenario and loss rate"""

        match self.scenario:
            case (
                constants.NO_LOSS
                | constants.TX_ACK_LOSS
                | constants.TX_ACK_SLOW
                | constants.RX_DATA_SLOW
                | constants.TX_ACK_DROP
                | constants.RX_DATA_DROP
            ):
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
