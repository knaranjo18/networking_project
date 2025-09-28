# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1

# --- Stubs you should implement elsewhere ---
def udt_rcv(sock):  # -> (pkt, addr)
    raise NotImplementedError
def udt_send(sock, addr, pkt): ...
def is_corrupt(pkt): ...
def has_seq(pkt, seq): ...
def extract_data(pkt): ...
def deliver_data(data): ...
def make_ack(seq): ...

class RDT22Receiver:
    def __init__(self, sock):
        self.sock = sock
        self.state = WAIT_0
        self.once = False               # same as oncethru
        self.last_ack = {0: None, 1: None}

    def run(self):
        while True:
            rcvpkt, addr = udt_rcv(self.sock)

            if self.state == WAIT_0:
                if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 0):
                    data = extract_data(rcvpkt)
                    deliver_data(data)
                    ack = make_ack(0)
                    udt_send(self.sock, addr, ack)
                    self.last_ack[0] = ack
                    self.once = True
                    self.state = WAIT_1
                else:  # corrupt or has_seq1
                    if self.once and self.last_ack[0]:
                        udt_send(self.sock, addr, self.last_ack[0])

            elif self.state == WAIT_1:
                if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 1):
                    data = extract_data(rcvpkt)
                    deliver_data(data)
                    ack = make_ack(1)
                    udt_send(self.sock, addr, ack)
                    self.last_ack[1] = ack
                    self.state = WAIT_0
                else:  # corrupt or has_seq0
                    if self.last_ack[1]:
                        udt_send(self.sock, addr, self.last_ack[1])
