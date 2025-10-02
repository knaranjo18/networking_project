import socket as soc
from Packets import Packet, DataPacket

# --- State constants ---
WAIT_CALL_0 = 0
WAIT_ACK_0  = 1
WAIT_CALL_1 = 2
WAIT_ACK_1  = 3

##Fill with code from part 1
def udt_rcv(sock: soc.socket) -> bytes:
    return sock.recv(1024)

def udt_send(sock: soc.socket, pkt: bytes):
    sock.sendall(pkt)

class RDT22Sender:
    def __init__(self, sock: soc.socket):
        self.sock = sock
        self.state = WAIT_CALL_0
        self.last_pkt: DataPacket | None = None  # buffer last sent packet

    def rdt_send(self, data: bytes):
        """Called by application to send one chunk of data"""
        if self.state == WAIT_CALL_0:
            self.last_pkt = DataPacket(data, 0)
            udt_send(self.sock, self.last_pkt.extract_data())
            self.statestate = WAIT_ACK_0

        elif self.state == WAIT_CALL_1:
            self.last_pkt = DataPacket(data, 1)
            udt_send(self.sock, self.last_pkt.extract_data())
            self.state = WAIT_ACK_1
        else:
            # If app calls at wrong time, ignore or block until ready
            pass

    def input(self):
        """Called when a packet arrives from receiver"""
        rcvpkt = udt_rcv(self.sock)

        if self.last_pkt is None:
            return

        if self.state == WAIT_ACK_0:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 0:
                self.state = WAIT_CALL_1
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.last_pkt.extract_data())

        elif self.state == WAIT_ACK_1:
            if not Packet.is_corrupt(rcvpkt) and Packet.ack_seq(rcvpkt) == 1:
                self.state = WAIT_CALL_0
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.last_pkt.extract_data())
