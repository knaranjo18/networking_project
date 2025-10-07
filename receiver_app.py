import argparse
import os
import socket as soc
import time

from constants import *
from Packets import DataPacket
from rdt22_receiver import RDT22Receiver


def handle_CLI():
    """Reads command line arguments to get output file name and scenario."""
    parser = argparse.ArgumentParser(description="Image receiver with RDT 2.2 protocol")
    parser.add_argument(
        "-o",
        "--output_file",
        default="rx_image",
        help="Output image base name (no extension)",
    )
    parser.add_argument(
        "-s",
        "--scenario",
        default=1,
        type=int,
        help="Data transfer scenario to implement",
    )
    args = parser.parse_args()
    return args.output_file, args.scenario


def receive_image(scenario: int, loss: float):
    """Receives an image over RDT 2.2. Returns (image_bytes, end_time)."""
    # Normalize loss to 0..1 if needed
    loss_rate = loss if 0.0 <= loss <= 1.0 else max(0.0, min(1.0, loss / 100.0))

    # Bind UDP socket to receiver address/port
    rx_sock = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    rx_sock.setsockopt(soc.SOL_SOCKET, soc.SO_REUSEADDR, 1)
    rx_sock.bind((RX_ADDR, RX_PORT))

    receiver = RDT22Receiver(rx_sock, scenario, loss_rate)

    # --- First packet: number of data packets to follow (8 bytes, big-endian) ---
    first_pkt = None
    while first_pkt is None:
        first_pkt = receiver.get_data_pkt()
    num_pkts = int.from_bytes(first_pkt.data, "big")

    # --- Receive the data packets ---
    data_pkt_list: list[DataPacket] = []
    data_pkt_idx = 0
    while data_pkt_idx < num_pkts:
        pkt = receiver.get_data_pkt()
        if pkt is not None:
            data_pkt_list.append(pkt)
            data_pkt_idx += 1  # <-- critical fix: advance the index

    # Reassemble payload
    image_bytes = b"".join(p.data for p in data_pkt_list)
    end_time = time.time()
    rx_sock.close()
    return image_bytes, end_time


def write_image_file(output_name: str, image_bytes: bytes):
    """Writes received bytes to ./data/<output_name>.bmp"""
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_folder, exist_ok=True)
    out_path = os.path.join(data_folder, f"{output_name}.bmp")
    with open(out_path, "wb") as f:
        f.write(image_bytes)
    print(f"Saved image to: {out_path} ({len(image_bytes)} bytes)")


if __name__ == "__main__":
    output_file, scenario = handle_CLI()

    # Single receive (you can loop losses externally if desired)
    # If your workflow expects sweep, wrap in a for-range like sender does.
    loss = 0  # start with no loss for receiver side by default
    image_bytes, end_time = receive_image(scenario, loss)
    write_image_file(output_file, image_bytes)
