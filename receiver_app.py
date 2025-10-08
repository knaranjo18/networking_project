import argparse
import os
import socket as soc
import time

from constants import *
from Packets import DataPacket
from rdt22_receiver import RDT22Receiver


def combine_packets(packet_list: list[DataPacket]) -> bytes:
    """Extract the data from the packets to a form a continuous byte array"""

    combined_bytes = b""

    # Extracts only the data from the packets
    for packet in packet_list:
        combined_bytes += packet.data

    return combined_bytes


def save_bmp(data: bytes, output_name: str):
    """Save an array of bytes to a BMP file on disk"""

    # Get image path
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    full_img_path = os.path.join(data_folder, output_name)

    print(f"Saving image to: {full_img_path}.bmp")

    # Write the image to file
    with open(f"{full_img_path}.bmp", "wb") as img_file:
        img_file.write(data)


def receive_image(scenario: int, loss_rate: float):
    rx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    with rx_soc:
        rx_soc.bind((RX_ADDR, RX_PORT))
        receiver = RDT22Receiver(rx_soc, scenario, loss_rate)

        # Receive initial packet that holds the number of expected packets
        while True:
            init_pkt = receiver.get_data_pkt()
            if init_pkt:
                num_pkts = int.from_bytes(init_pkt.data, "big")
                break

        data_pkt_idx = 1

        data_pkt_list: list[DataPacket] = []

        while data_pkt_idx <= num_pkts:
            curr_pkt = receiver.get_data_pkt()

            if curr_pkt:
                data_pkt_list.append(curr_pkt)
                data_pkt_idx += 1

        end_time = time.time()

        return combine_packets(data_pkt_list), end_time


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument(
        "-o",
        "--output_file",
        default="rx_img",
        help="The name to save the image as (no extension)",
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


def write_time_file(scenario: int, iter: int, loss: int, end_time: float) -> None:
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_folder, exist_ok=True)

    if scenario == NO_LOSS:
        time_file = "no_loss_end_times.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = "tx_ack_loss_end_times.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = "rx_data_loss_end_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)

    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{loss},{end_time}\n")


if __name__ == "__main__":
    output_file, scenario = handle_CLI()

    # Iterate over loss rate between 0 to 60 percent with increments of 5
    for loss in range(0, 61, 5):
        for iter in range(0, NUM_ITER):
            print(f"Scene {scenario}\t\tLoss {loss}%  \tIter {iter}")
            image_bytes, end_time = receive_image(scenario, loss / 100)

            write_time_file(scenario, iter, loss, end_time)

            save_bmp(image_bytes, f"{output_file}")
