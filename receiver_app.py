import argparse
import os
import socket as soc
import time

from constants import *
from Packets import DataPacket
from rdt22_receiver import RDT22Receiver


def save_bmp(data: bytes, output_name: str):
    """Save an array of bytes to a BMP file on disk"""

    # Get image path
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    full_img_path = os.path.join(data_folder, output_name)

    print(f"Saving image to: {full_img_path}")

    # Write the image to file
    with open(f"{full_img_path}", "wb") as img_file:
        img_file.write(data)


def check_image(data: bytes, image_file_name: str) -> bool:
    """Compares received image bytes to an input image file to verify correctness"""

    # Get image path
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    full_img_path = os.path.join(data_folder, image_file_name)

    # Read in image and convert to bytes
    try:
        with open(f"{full_img_path}", "rb") as img_file:
            img_bytes = img_file.read()
    except:
        print(f"Could not find file: {full_img_path}\nExiting program!")
        exit()

    return data == img_bytes


def receive_image(scenario: int, loss_rate: float):
    rx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    with rx_soc:
        rx_soc.bind((RX_ADDR, RX_PORT))
        receiver = RDT22Receiver(rx_soc, scenario, loss_rate)

        # Receive initial packet that holds the number of expected packets
        while True:
            init_pkt = receiver.get_data()
            if init_pkt:
                num_pkts = int.from_bytes(init_pkt, "big")
                break

        data_pkt_idx = 1

        data_pkt_list: list[bytes] = []

        while data_pkt_idx <= num_pkts:
            curr_pkt = receiver.get_data()

            if curr_pkt:
                data_pkt_list.append(curr_pkt)
                data_pkt_idx += 1

        end_time = time.time()

        return b"".join(data_pkt_list), end_time


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument(
        "-o",
        "--output_file",
        default="rx_img.bmp",
        help="The name to save the image as.",
    )
    parser.add_argument(
        "-i",
        "--input_file",
        default="megamind.bmp",
        help="The name of the image compare against.",
    )
    parser.add_argument(
        "-s",
        "--scenario",
        default=1,
        type=int,
        help="Data transfer scenario to implement.",
    )

    args = parser.parse_args()

    return args.output_file, args.scenario, args.input_file


def write_time_file(
    scenario: int, iter: int, loss: int, end_time: float, image_size: int
) -> None:
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_folder, exist_ok=True)

    if scenario == NO_LOSS:
        time_file = "no_loss_end_times.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = "tx_ack_loss_end_times.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = "rx_data_loss_end_times.txt"
    elif scenario == TX_ACK_DROP:
        time_file = "tx_ack_drop_end_times.txt"
    elif scenario == RX_DATA_DROP:
        time_file = "rx_data_drop_end_times.txt"
    elif scenario == TX_ACK_SLOW:
        time_file = "tx_ack_slow_end_times.txt"
    elif scenario == RX_DATA_SLOW:
        time_file = "rx_data_slow_end_times.txt"
    else:
        print("Invalid scenario number!")
        time_file = f"{scenario}_start_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)

    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{loss},{end_time},{image_size}\n")


if __name__ == "__main__":
    output_file, scenario, input_file = handle_CLI()

    # Iterate over loss rate between 0 to 60 percent with increments of 5
    for loss in range(0, 61, 5):
        for iter in range(0, NUM_ITER):
            print(f"Scene {scenario}\t\tLoss {loss}%  \tIter {iter}")
            image_bytes, end_time = receive_image(scenario, loss / 100)

            if not check_image(image_bytes, input_file):
                print("Received image does not match the original image!")
                exit()

            write_time_file(scenario, iter, loss, end_time, len(image_bytes))

            save_bmp(image_bytes, f"{output_file}")
