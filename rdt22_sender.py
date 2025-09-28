# --- State constants ---
WAIT_CALL_0 = 0
WAIT_ACK_0  = 1
WAIT_CALL_1 = 2
WAIT_ACK_1  = 3

##Fill with code from part 1
def udt_send(sock, addr, pkt): ...
def udt_rcv(sock): ...
def make_pkt(seq, data): ...
def is_corrupt(pkt): ...
def is_ack(pkt, seq): ...

class RDT22Sender:
    def __init__(self, sock, peer):
        self.sock = sock
        self.peer = peer
        self.state = WAIT_CALL_0
        self.last_pkt = None  # buffer last sent packet

    def rdt_send(self, data):
        """Called by application to send one chunk of data"""
        if self.state == WAIT_CALL_0:
            self.last_pkt = make_pkt(0, data)
            udt_send(self.sock, self.peer, self.last_pkt)
            self.state = WAIT_ACK_0

        elif self.state == WAIT_CALL_1:
            self.last_pkt = make_pkt(1, data)
            udt_send(self.sock, self.peer, self.last_pkt)
            self.state = WAIT_ACK_1
        else:
            # If app calls at wrong time, ignore or block until ready
            pass

    def input(self):
        """Called when a packet arrives from receiver"""
        rcvpkt, _ = udt_rcv(self.sock)

        if self.state == WAIT_ACK_0:
            if not is_corrupt(rcvpkt) and is_ack(rcvpkt, 0):
                self.state = WAIT_CALL_1
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.peer, self.last_pkt)

        elif self.state == WAIT_ACK_1:
            if not is_corrupt(rcvpkt) and is_ack(rcvpkt, 1):
                self.state = WAIT_CALL_0
            else:  # corrupt or wrong ACK
                udt_send(self.sock, self.peer, self.last_pkt)
