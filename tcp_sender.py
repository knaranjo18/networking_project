import random
import socket as soc
import time
from datetime import datetime

import constants
from Packets import DataPacket, Packet

class TCPSender:
    def __init__(self, sock: soc.socket, scenario: int, loss_rate: float, window_size: int, timeout: float):
        self.sock = sock
        self.sock.settimeout(timeout)  # resend if no ACK within timeout

        self.window_size = window_size
        self.sndpkt: list[DataPacket] = [
            DataPacket(b"", 1)
        ] * self.window_size  # buffer last sent packets

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

    def rdt_send(self, curr_packet: DataPacket) -> bool:
        """
        Called by application to send one chunk of data. Return true of able to succesfully send packet. 
        Return false if reached limit of packets in flight
        """
        if self.nextseqnum < self.base + self.window_size:
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Sending Base: {self.base} \t NextSeqNum: {self.nextseqnum}"
                )

            # Send packet and add to buffer of previosly sent packets
            self.sndpkt[self.nextseqnum % self.window_size] = curr_packet
            self.udt_send(self.sock, curr_packet.to_bytes())
            
            if self.base == self.nextseqnum:
                pass  # start timer handled by input() so do nothing here
            
            self.nextseqnum += 1
            return True
        
        # window is full data cannot be sent
        return False

    def do_resend(self) -> None:
        """Resend all packets in the window starting from base to nextseqnum-1"""
        for seq in range(self.base, self.nextseqnum):
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Resending seq#{seq}")
            
            pkt = self.sndpkt[seq % self.window_size]
            self.udt_send(self.sock, pkt.to_bytes())

    def input(self, last_acks: bool) -> bool:
        """Called when a packet arrives from receiver. Returns True if done waiting for input"""

        # Caught up, done waiting
        if self.base == self.nextseqnum:
            return True

        # No packets sent yet, need to keep waiting
        if len(self.sndpkt) == 0:
            return False

        try:
            rcvpkt = self.udt_rcv(self.sock)
        except soc.timeout:
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Timed out")
           
            # Resend all packets in the window on timeout
            self.do_resend()
            
            # restart timer same as just waiting again
            return False

        rcvpkt = self.__corrupt_ACK_bytes(rcvpkt)
        ackpkt = Packet(rcvpkt)
        
        if not ackpkt.is_corrupt():
            if constants.DEBUG_PRINT:
                print(
                    f"[{datetime.now().strftime('%S.%f')}] Got ACK for seq num# {ackpkt.seq_num}"
                )
            
            # Theoretically we can make the sequence number go backwards due to sequential file transfers, exit early in this case
            if ackpkt.seq_num < self.base and constants.TX_ACK_DROP == self.scenario:
                return True

            # This does cumulitive ACK since we move up to the lastest succesful ACK
            self.base = ackpkt.seq_num + 1
            
            if self.base == self.nextseqnum:
                return True  # stop timer 
                # we don't need to stop waiting as we will only call the receive function when we need to get an ACK
                # Return True to indicates that all expected ACKs have been received
            else:
                pass  # restart timer same as just waiting again

        else:  # corrupt ACK
            if constants.DEBUG_PRINT:
                print(f"[{datetime.now().strftime('%S.%f')}] Got corrupt ACK")
            
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
