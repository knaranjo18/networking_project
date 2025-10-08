import argparse
import os
import socket as soc
import time

from constants import *
from Packets import DataPacket
from rdt22_receiver import RDT22Receiver


def handle_CLI():
    """Reads command line arguments to get output file name, scenario, and (optional) receiver loss% for scenario 2."""
    parser = argparse.ArgumentParser(description="Image receiver with RDT 2.2 protocol")
    parser.add_argument("-o", "--output_file", default="rx_image",
                        help="Output image base name (no extension)")
    parser.add_argument("-s", "--scenario", default=1, type=int,
                        help="Data transfer scenario: 0=NO_LOSS, 1=TX_ACK_LOSS, 2=RX_DATA_LOSS")
    parser.add_argument("-l", "--loss", default=0, type=int,
                        help="Receiver loss percent for RX_DATA_LOSS (0–100)")
    args = parser.parse_args()
    return args.output_file, args.scenario, args.loss


def write_image_file(output_name: str, image_bytes: bytes):
    """Writes received bytes to ./data/<output_name>.bmp"""
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_folder, exist_ok=True)
    out_path = os.path.join(data_folder, f"{output_name}.bmp")
    with open(out_path, "wb") as f:
        f.write(image_bytes)
    print(f"Saved image to: {out_path} ({len(image_bytes)} bytes)")


def receive_one_image(receiver: RDT22Receiver) -> bytes:
    """Receive exactly one image using an existing RDT22Receiver; return raw bytes."""
    # First packet: number of data packets (8 bytes big-endian)
    first_pkt: DataPacket | None = None
    while first_pkt is None:
        first_pkt = receiver.get_data_pkt()
    num_pkts = int.from_bytes(first_pkt.data, "big")

    # Receive the data packets
    data_pkt_list: list[DataPacket] = []
    got = 0
    while got < num_pkts:
        pkt = receiver.get_data_pkt()
        if pkt is not None:
            data_pkt_list.append(pkt)
            got += 1

    return b"".join(p.data for p in data_pkt_list)


if __name__ == "__main__":
    output_base, scenario, rx_loss_percent = handle_CLI()

    # Bind once and keep listening
    rx_sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    rx_sock.setsockopt(soc.SOL_SOCKET, soc.SO_REUSEADDR, 1)
    rx_sock.bind((RX_ADDR, RX_PORT))

    # Apply receiver-side loss only for scenario 2
    rx_loss_rate = (rx_loss_percent / 100.0) if scenario == RX_DATA_LOSS else 0.0
    receiver = RDT22Receiver(rx_sock, scenario, rx_loss_rate)

    idx = 0
    try:
        while True:
            start = time.time()
            image_bytes = receive_one_image(receiver)
            end = time.time()
            write_image_file(f"{output_base}_{idx}", image_bytes)
            print(f"Image #{idx} received in {end - start:.3f}s (scenario={scenario}, rx_loss={rx_loss_percent}%)")
            idx += 1
    except KeyboardInterrupt:
        print("\nShutting down receiver.")
    finally:
        rx_sock.close()
