import random
import socket as soc
import time
from datetime import datetime

import constants
from Packets import DataPacket, Packet, SynPacket, FinPacket, AckPacket
from collections import deque

ALPHA = 0.125
BETA = 0.25

class TCPSender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float, c_control: int):
        self.sock = sock
        self.curr_timeout = constants.TIMEOUT_FIXED[0]
        self.sock.settimeout(self.curr_timeout)  # resend if no ACK within timeout
        self.congest_control = c_control
        self.ssthresh = 2**16-1 # 64 kB
        self.dupACKcount = 0
        self.free_rx_buffer = 2**16-1

        self.prev_ack = -1

        # Used to keep track of RTT and timeout and congestion window size for plotting later
        self.cwnd_list: list[tuple[float, int]] = []
        self.sampRTT_list: list[tuple[float, float]] = []
        self.timeout_list: list[tuple[float, float]] = []

        self.start_time = time.time()

        self.estimatedRTT = None
        self.devRTT = None

        self.cwnd = constants.MAX_DATA_SIZE
        self.sndpkt_buffer: deque[tuple[DataPacket, float]] = deque()

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
                    
                ack_packet = AckPacket(ack_num=synack_pkt.seq_num + 1, src_port=constants.TX_PORT, dst_port=constants.RX_PORT, seq_num=1)
                self.sndpkt_buffer.append((ack_packet, -1))
                self.nextseqnum += 1
                self.udt_send(self.sock, ack_packet.to_bytes())
                connected = True
   
    def close_connection(self) -> None:
        fin_pkt = FinPacket(self.nextseqnum, constants.TX_PORT, constants.RX_PORT)
        fail_cnt = 0
        
        while fail_cnt < 8:
            self.udt_send(self.sock, fin_pkt.to_bytes())

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
        if self.nextseqnum < self.base + self.cwnd and (self.nextseqnum - self.base) < self.free_rx_buffer:
            # Send packet and add to buffer of previously sent packets
            self.sndpkt_buffer.append((curr_packet, time.time()))
            self.udt_send(self.sock, curr_packet.to_bytes())
            
            self.nextseqnum += curr_packet.data_len

            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Sending Base: {self.base} \t NextSeqNum: {self.nextseqnum}"
                )
            return True
        
        # window is full data cannot be sent
        return False

    def do_resend(self) -> None:
        """Resend all packets in the window starting from base to nextseqnum-1"""
        for i in range(len(self.sndpkt_buffer)):
            resend_pkt = self.sndpkt_buffer[i][0]
            self.sndpkt_buffer[i] = (self.sndpkt_buffer[i][0], time.time())  # Update the start time of packet

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Resending seq#{resend_pkt.seq_num}")
            
            self.udt_send(self.sock, resend_pkt.to_bytes())

    def clean_buffer(self) -> None:
        while True:
            if self.sndpkt_buffer and self.sndpkt_buffer[0][0].seq_num < self.base:
                acked_pkt = self.sndpkt_buffer.popleft()

                # This means the packet was just acknowledged and not part of a cumalitive ack
                if acked_pkt[0].seq_num + acked_pkt[0].data_len == self.base: 
                    sampleRTT = time.time() - acked_pkt[1]
                    self.updateTimeout(sampleRTT)
            else:
                break

    def updateTimeout(self, sampleRTT) -> None:
        # Initialization value, should only run once
        if not self.estimatedRTT:
            self.estimatedRTT = sampleRTT

        self.estimatedRTT = (1 - ALPHA) * self.estimatedRTT + (ALPHA * sampleRTT)

        # Initialization value, should only run once
        if not self.devRTT:
            self.devRTT = 1/8 * self.estimatedRTT

        self.devRTT = (1 - BETA) * self.devRTT + (BETA * abs(sampleRTT - self.estimatedRTT))

        self.curr_timeout = self.estimatedRTT + 4 * self.devRTT

        if constants.DEBUG_PRINT:
            print(f"[{datetime.now().strftime('%S.%f')}] Sample RTT {sampleRTT}, devRTT {self.devRTT}, new timeout = {self.curr_timeout / 1e-3} ms")

        self.sock.settimeout(self.curr_timeout)

        curr_time = time.time() - self.start_time
        self.timeout_list.append((curr_time, self.curr_timeout))
        self.sampRTT_list.append((curr_time, sampleRTT))


    def slow_start(self, isTimeout) -> None:
        if isTimeout:
            self.ssthresh = self.cwnd/2
            self.cwnd = constants.MAX_DATA_SIZE

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Decreasing CWND to {self.cwnd}. SSTHresh is now {self.ssthresh}")    

            self.cwnd_list.append((time.time() - self.start_time, self.cwnd))
        else:
            if self.cwnd >= self.ssthresh:
                self.linear_cwnd_increase()
            else:
                self.exponential_cwnd_increase()


    def linear_cwnd_increase(self) -> None:
        potential_new_cwnd = self.cwnd + constants.MAX_DATA_SIZE * (constants.MAX_DATA_SIZE / self.cwnd)
        if potential_new_cwnd <= self.free_rx_buffer:
            self.cwnd = potential_new_cwnd

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Increasing CWND to {self.cwnd}")    
                

    def exponential_cwnd_increase(self) -> None:
        if self.cwnd + constants.MAX_DATA_SIZE <= self.free_rx_buffer:
            self.cwnd += constants.MAX_DATA_SIZE

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Increasing CWND to {self.cwnd}")    
    
        self.cwnd_list.append((time.time() - self.start_time, self.cwnd))

    def AIMD(self, isTimeout) -> None:
        if isTimeout:
            potential_cwnd = self.cwnd * 0.5

            if potential_cwnd < constants.MAX_DATA_SIZE:
                self.cwnd = constants.MAX_DATA_SIZE
            else:
                self.cwnd = potential_cwnd

            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Decreasing CWND to {self.cwnd}")    

            self.cwnd_list.append((time.time() - self.start_time, self.cwnd))
        else:
            self.linear_cwnd_increase()

    def update_cwnd_ack(self, ack_num) -> None:
        if ack_num == self.prev_ack:
            self.dupACKcount += 1
            new_ack = False
        else:
            self.prev_ack = ack_num
            self.dupACKcount = 0
            new_ack = True

        if self.congest_control == constants.SLOW_START:
            if new_ack:
                self.slow_start(isTimeout=False)
        elif self.congest_control == constants.AIMD:
            if new_ack:
                self.AIMD(isTimeout=False)

   
    def update_cwnd_timeout(self) -> None:
        self.dupACKcount = 0

        if self.congest_control == constants.SLOW_START:
            self.slow_start(isTimeout=True)
        elif self.congest_control == constants.AIMD:
            self.AIMD(isTimeout=True)

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
           
            self.update_cwnd_timeout()
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

            # This does cumulitive ACK since we move up to the latest succesful ACK
            self.base = ackpkt.ack_num
            self.free_rx_buffer = ackpkt.window_size

            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Receiver Free Buffer Size {self.free_rx_buffer} bytes"
                )
            

            self.update_cwnd_ack(ackpkt.ack_num)
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
