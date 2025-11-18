import argparse
import os
import socket as soc
import time
from datetime import datetime

from constants import *
from Packets import DataPacket
from rdt22_sender import RDT22Sender


def make_data_pkt(data: bytes) -> list[DataPacket]:
    """Helper function that takes an array of bytes and converts it to a list of Data Packets."""

    num_bytes = len(data)

    # Doing integer division to get the number of full packets
    num_full_pkts = num_bytes // MAX_DATA_SIZE

    pkt_list = []

    seq_num = 1

    # First packet sent will contain the number of data packets to follow
    num_data_packets = num_full_pkts + 1
    num_packets_bytes = num_data_packets.to_bytes(8, "big")
    first_packet = DataPacket(num_packets_bytes, seq_num)
    seq_num += 1

    pkt_list.append(first_packet)

    # Extract the amount of data required per packet
    for i in range(num_full_pkts):
        pkt_list.append(
            DataPacket(data[i * MAX_DATA_SIZE : (i + 1) * MAX_DATA_SIZE], seq_num)
        )
        seq_num += 1  # alternates between 0 and 1

    # Add the last packet with padding to get the full size
    pkt_list.append(DataPacket(data[num_full_pkts * MAX_DATA_SIZE :], seq_num))

    return pkt_list


def image_file_2_bytes(image_file_name: str) -> bytes:
    """Reads an image from a filename and converts it to bytes"""

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

    return img_bytes


def handle_CLI() -> str:
    "Reads command line arguments to get the input file name"

    parser = argparse.ArgumentParser(description="Image sender with RDT 1.0 protocol")

    parser.add_argument(
        "-i",
        "--input_file",
        default="megamind.bmp",
        help="The name of the image to send.",
    )
    parser.add_argument(
        "-s",
        "--scenario",
        default=1,
        type=int,
        help="Data transfer scenario to implement.",
    )

    args = parser.parse_args()

    return args.input_file, args.scenario


def send_image(bytes_image: bytes, scenario: int, loss: float) -> float:
    """Main loop that uses RDT 2.2 to send bytes to receiver"""

    # Create socket that will be used to send all packets
    tx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    with tx_soc:
        # (Minimal change) Removed UDP connect; rdt22_sender uses recvfrom() for ACKs

        data_packet_list = make_data_pkt(bytes_image)

        sender = RDT22Sender(tx_soc, scenario, loss)

        data_idx = 0

        start_time = time.time()

        # Sends all data packets
        while data_idx < len(data_packet_list):
            print(f"[{datetime.now().strftime('%S.%f')}] Sending packet {data_idx + 1}")
            sent = sender.rdt_send(data_packet_list[data_idx])
            if sent:
                data_idx += 1
            sender.input()

        # Ensure all packets are ACKed before finishing
        while not sender.input():
            pass

        return start_time


def write_time_file(
    scenario: int, iter: int, loss: int, start_time: float, data_length: float
) -> None:
    """Write start time to file for later analysis"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_folder, exist_ok=True)  # <-- ensure folder exists

    if scenario == NO_LOSS:
        time_file = "no_loss_start_times.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = "tx_ack_loss_start_times.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = "rx_data_loss_start_times.txt"
    elif scenario == TX_ACK_DROP:
        time_file = "tx_ack_drop_start_times.txt"
    elif scenario == RX_DATA_DROP:
        time_file = "rx_data_drop_start_times.txt"
    elif scenario == TX_ACK_SLOW:
        time_file = "tx_ack_slow_start_times.txt"
    elif scenario == RX_DATA_SLOW:
        time_file = "rx_data_slow_start_times.txt"
    else:
        print("Invalid scenario number!")
        time_file = f"{scenario}_start_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)

    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{loss},{start_time},{data_length}\n")


if __name__ == "__main__":
    # Process command line arguments
    input_file, scenario = handle_CLI()

    bytes_image = image_file_2_bytes(input_file)

    # Iterate over loss rate between 0 to 60 percent with increments of 5
    for loss in range(0, 61, 5):
        for iter in range(0, NUM_ITER):
            print(
                f"[{datetime.now().strftime('%S.%f')}] Scene {scenario}\t\tLoss {loss}%  \tIter {iter}"
            )
            start_time = send_image(bytes_image, scenario, loss / 100)
            write_time_file(scenario, iter, loss, start_time, len(bytes_image))
            time.sleep(0.15)  # Wait a second between steps for things to settle
