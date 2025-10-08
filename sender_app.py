import argparse
import os
import socket as soc
import time

from constants import *
from Packets import DataPacket
from rdt22_sender import RDT22Sender


def make_data_pkt(data: bytes) -> list[DataPacket]:
    """Helper function that takes an array of bytes and converts it to a list of Data Packets."""
    num_bytes = len(data)
    num_full_pkts = num_bytes // DataPacket.DATA_SIZE

    pkt_list: list[DataPacket] = []
    seq_num = 0

    # First packet carries the number of data packets to follow (8 bytes, big-endian)
    num_data_packets = num_full_pkts + 1
    num_packets_bytes = num_data_packets.to_bytes(8, "big")
    pkt_list.append(DataPacket(num_packets_bytes, seq_num))
    seq_num ^= 1

    # Full-sized packets
    for i in range(num_full_pkts):
        start = i * DataPacket.DATA_SIZE
        end = (i + 1) * DataPacket.DATA_SIZE
        pkt_list.append(DataPacket(data[start:end], seq_num))
        seq_num ^= 1

    # Final (possibly partial) packet
    pkt_list.append(DataPacket(data[num_full_pkts * DataPacket.DATA_SIZE :], seq_num))
    return pkt_list


def image_file_2_bytes(image_file_name: str) -> bytes:
    """Reads an image by base name (no extension) and returns its bytes."""
    here = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(here, "data")
    primary = os.path.join(data_folder, f"{image_file_name}.bmp")
    fallback = os.path.join(here, f"{image_file_name}.bmp")

    for path in (primary, fallback):
        try:
            with open(path, "rb") as img_file:
                return img_file.read()
        except FileNotFoundError:
            continue

    print(f"Could not find file in either:\n  {primary}\n  {fallback}\nExiting program!")
    exit(1)


def handle_CLI():
    """Reads command line arguments to get the input file name and scenario."""
    parser = argparse.ArgumentParser(description="Image sender with RDT 2.2 protocol")
    parser.add_argument("-i", "--input_file", default="megamind",
                        help="Image base name to send (no extension)")
    parser.add_argument("-s", "--scenario", default=1, type=int,
                        help="Data transfer scenario: 0=NO_LOSS, 1=TX_ACK_LOSS, 2=RX_DATA_LOSS")
    args = parser.parse_args()
    return args.input_file, args.scenario


def send_image(bytes_image: bytes, scenario: int, loss: float) -> float:
    """Main loop that uses RDT 2.2 to send bytes to receiver. Returns start_time."""
    tx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    with tx_soc:
        # NOTE: We don't connect(). rdt22_sender.udt_rcv() uses recvfrom() safely.
        data_packet_list = make_data_pkt(bytes_image)
        sender = RDT22Sender(tx_soc, scenario, loss)

        data_idx = 0
        start_time = time.time()

        while data_idx < len(data_packet_list):
            sender.rdt_send(data_packet_list[data_idx])
            resent = sender.input()
            if not resent:
                data_idx += 1

        return start_time


def write_time_file(scenario: int, iter: int, loss: int, start_time: float) -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    results_folder = os.path.join(here, "results")
    os.makedirs(results_folder, exist_ok=True)  # ensure folder exists

    if scenario == NO_LOSS:
        time_file = "no_loss_start_times.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = "tx_ack_loss_start_times.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = "rx_data_loss_start_times.txt"
    else:
        time_file = f"scenario_{scenario}_start_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)
    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{loss},{start_time}\n")


if __name__ == "__main__":
    input_file, scenario = handle_CLI()
    bytes_image = image_file_2_bytes(input_file)

    # Iterate loss rate 0..60% in steps of 5 (sender-side loss only matters for scenario 1)
    for loss in range(0, 61, 5):
        for iter in range(0, NUM_ITER):
            start_time = send_image(bytes_image, scenario, loss / 100.0)
            write_time_file(scenario, iter, loss, start_time)
            time.sleep(1)  # brief pause between runs
