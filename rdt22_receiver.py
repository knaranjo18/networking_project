import socket as soc

# --- State constants ---
WAIT_0 = 0
WAIT_1 = 1

# --- Stubs you should implement elsewhere ---
def udt_rcv(sock: soc.socket) -> bytes:
    raise NotImplementedError
def udt_send(sock: soc.socket, pkt: bytes): ...
def is_corrupt(pkt: bytes) -> bool: ...
def has_seq(pkt: bytes, seq: int): ...
def extract_data(pkt: bytes) -> bytes: ...
def deliver_data(data: bytes) -> bytes: ...
def make_ack(seq: int) -> bytes: ...

class RDT22Receiver:
    def __init__(self, sock: soc.socket):
        self.sock = sock
        self.state = WAIT_0
        self.once = False               # same as oncethru
        self.last_ack: dict[int, bytes | None] = {0: None, 1: None}

    def run(self):
        while True:
            rcvpkt = udt_rcv(self.sock)

            if self.state == WAIT_0:
                if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 0):
                    data = extract_data(rcvpkt)
                    deliver_data(data)
                    ack = make_ack(0)
                    udt_send(self.sock, ack)
                    self.last_ack[0] = ack
                    self.once = True
                    self.state = WAIT_1
                else:  # corrupt or has_seq1
                    if self.once and self.last_ack[0]:
                        udt_send(self.sock, self.last_ack[0])

            elif self.state == WAIT_1:
                if not is_corrupt(rcvpkt) and has_seq(rcvpkt, 1):
                    data = extract_data(rcvpkt)
                    deliver_data(data)
                    ack = make_ack(1)
                    udt_send(self.sock, ack)
                    self.last_ack[1] = ack
                    self.state = WAIT_0
                else:  # corrupt or has_seq0
                    if self.last_ack[1]:
                        udt_send(self.sock, self.last_ack[1])
