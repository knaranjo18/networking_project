import random
import socket as soc
import time
from datetime import datetime

import constants
from Packets import DataPacket, Packet, SynPacket, FinPacket, AckPacket
from collections import deque

class TCPSender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float, init_window_size: int, init_timeout: float):
        self.sock = sock
        self.curr_timeout = init_timeout
        self.sock.settimeout(init_timeout)  # resend if no ACK within timeout

        self.window_size = init_window_size
        self.sndpkt_buffer: deque[DataPacket] = deque()

        # Keep track of window state
        self.base = 1
        self.nextseqnum = 1

        self.scenario = scenario
        self.loss_rate = (
            loss_rate
            if 0.0 <= loss_rate <= 1.0
            else max(0.0, min(1.0, loss_rate / 100.0))
        )   # Normalize loss_rate to 0..1 if user passes 0..100


    def udt_rcv(self, sock: soc.socket) -> bytes:
        # Use recvfrom on UDP (works without connect())
        data, _ = sock.recvfrom(constants.MAX_PACKET_SIZE)
        return data

    def udt_send(self, sock: soc.socket, pkt: bytes):
        if self.scenario == constants.TX_ACK_SLOW:
            time.sleep(1)

        if not self.__drop_Data_packet():
            sock.sendto(pkt, (constants.RX_ADDR, constants.RX_PORT))

    def establish_connection(self) -> None:
        syn_packet = SynPacket(seq_num=0, src_port=constants.TX_PORT, dst_port=constants.RX_PORT)
        connected = False
        
        while not connected:
            self.udt_send(self.sock, syn_packet.to_bytes())

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Sent SYN packet")
            
            try:
                rcvpkt_bytes = self.udt_rcv(self.sock)
                synack_pkt = Packet(rcvpkt_bytes)
            except soc.timeout:
                if constants.DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] SYN Timed out after {self.curr_timeout / 1e-3} ms")
                
                continue

            if not synack_pkt.is_corrupt() and synack_pkt.syn and synack_pkt.ack:
                if constants.DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] Received good SYNACK. Sending Final ACK. Connection Established.")
                    
                ack_packet = AckPacket(synack_pkt.seq_num + 1, src_port=constants.TX_PORT, dst_port=constants.RX_PORT)
                self.sndpkt_buffer.append(ack_packet)
                self.udt_send(self.sock, ack_packet)
                connected = True
   
    def close_connection(self) -> None:
        fin_pkt = FinPacket(self.nextseqnum, constants.TX_PORT, constants.RX_PORT)
        fail_cnt = 0
        
        while fail_cnt < 8:
            self.udt_send(self.sock, fin_pkt)

            if constants.DEBUG_PRINT:
                        print(f"[{datetime.now().strftime('%S.%f')}] Ending connection, sending FIN Packet.")

            try:
                rcvpkt_bytes = self.udt_rcv(self.sock)
                finack_pkt = Packet(rcvpkt_bytes)

                if not finack_pkt.is_corrupt() and finack_pkt.ack and finack_pkt.fin:
                    if constants.DEBUG_PRINT:
                        print(f"[{datetime.now().strftime('%S.%f')}] Received good FINACK. Connection Ended.")
                    return
                else:
                    if constants.DEBUG_PRINT:
                        print(f"[{datetime.now().strftime('%S.%f')}] Received bad FINACK.")
                    fail_cnt += 1

                break
            except soc.timeout:
                if constants.DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] FINACK Timed out after {self.curr_timeout / 1e-3} ms")
                
                fail_cnt += 1

        if constants.DEBUG_PRINT:
            print(f"[{datetime.now().strftime('%S.%f')}] FIN Packet ACK timed out 8 times. Connection ended")



    def tcp_send(self, curr_packet: DataPacket) -> bool:
        """
        Called by application to send one chunk of data. Return true of able to succesfully send packet. 
        Return false if reached limit of packets in flight
        """
        if self.nextseqnum < self.base + self.window_size:
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Sending Base: {self.base} \t NextSeqNum: {self.nextseqnum}"
                )

            # Send packet and add to buffer of previously sent packets
            self.sndpkt_buffer.append(curr_packet)
            self.udt_send(self.sock, curr_packet.to_bytes())
            
            self.nextseqnum += curr_packet.data_len
            return True
        
        # window is full data cannot be sent
        return False

    def do_resend(self) -> None:
        """Resend all packets in the window starting from base to nextseqnum-1"""
        for resend_pkt in self.sndpkt_buffer:
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Resending seq#{resend_pkt.seq_num}")
            
            self.udt_send(self.sock, resend_pkt.to_bytes())

    def clean_buffer(self) -> None:
        while True:
            if self.sndpkt_buffer and self.sndpkt_buffer[0].seq_num < self.base:
                self.sndpkt_buffer.popleft()
            else:
                break

    def input(self, last_acks: bool) -> bool:
        """Called when a packet arrives from receiver. Returns True if done waiting for input"""

        # Caught up, done waiting
        if self.base == self.nextseqnum:
            return True

        # No packets sent yet, need to keep waiting
        if len(self.sndpkt_buffer) == 0:
            return False

        try:
            rcvpkt_bytes = self.udt_rcv(self.sock)
        except soc.timeout:
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Timed out after {self.curr_timeout / 1e-3} ms")
           
            # Resend all packets in the window on timeout
            self.do_resend()
            
            # restart timer same as just waiting again
            return False

        rcvpkt_bytes = self.__corrupt_ACK_bytes(rcvpkt_bytes)
        ackpkt = Packet(rcvpkt_bytes)
        
        if not ackpkt.is_corrupt():
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Got ACK num# {ackpkt.ack_num}"
                )
            
            # Theoretically we can make the sequence number go backwards due to sequential file transfers, exit early in this case
            if ackpkt.ack_num < self.base and constants.TX_ACK_DROP == self.scenario:
                return True

            # This does cumulitive ACK since we move up to the lastest succesful ACK
            self.base = ackpkt.ack_num
            self.clean_buffer()
            
            if self.base == self.nextseqnum:
                return True  # stop timer 
                # we don't need to stop waiting as we will only call the receive function when we need to get an ACK
                # Return True to indicates that all expected ACKs have been received
            else:
                pass  # restart timer same as just waiting again

        else:  # corrupt ACK
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Got corrupt ACK. Ignoring.")
            
            # On the last set of transmitions even if ACK is corrupt, we slide the
            # windows as there aren't later ACKs to correctly move the window
            if last_acks:
                self.base += 1
                if self.base == self.nextseqnum:
                    return True
                
            # do nothing else if corrupt

        return False

    def __drop_Data_packet(self) -> bool:
        dropPacket = False
        
        if self.scenario == constants.RX_DATA_DROP:
            if random.random() < self.loss_rate:
                if constants.DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] Data Packet dropped")
                
                dropPacket = True
        
        return dropPacket

    def __corrupt_ACK_bytes(self, rx_bytes: bytes) -> bytes:
        """Randomly corrupts ACK packets depending on the scenario and loss rate"""

        match self.scenario:
            case (
                constants.NO_LOSS
                | constants.RX_DATA_LOSS
                | constants.TX_ACK_SLOW
                | constants.RX_DATA_SLOW
                | constants.RX_DATA_DROP
                | constants.TX_ACK_DROP
            ):
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
