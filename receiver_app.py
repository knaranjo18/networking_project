import argparse
import os
import socket as soc
import time

from datetime import datetime
from constants import *
from tcp_receiver import TCPReceiver


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
        receiver = TCPReceiver(rx_soc, scenario, loss_rate)

        receiver.establish_connection()
        connected = True

        data_pkt_list: list[bytes] = []

        while connected:
            curr_pkt = receiver.get_data()

            if curr_pkt:
                if curr_pkt == -1:
                    connected = False
                else:
                    data_pkt_list.append(curr_pkt)

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
    
    parser.add_argument("-x", "--xtype", default="loss", type=str, help="X-axis type. loss, timeout, window")

    args = parser.parse_args()

    return args.output_file, args.scenario, args.input_file, args.xtype


def write_time_file(
    scenario: int, iter: int, x_axis_val: int, x_axis_type: int, end_time: float, image_size: int
) -> None:
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_folder, exist_ok=True)

    if scenario == NO_LOSS:
        time_file = f"no_loss_end_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = f"tx_ack_loss_end_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = f"rx_data_loss_end_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_DROP:
        time_file = f"tx_ack_drop_end_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_DROP:
        time_file = f"rx_data_drop_end_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_SLOW:
        time_file = f"tx_ack_slow_end_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_SLOW:
        time_file = f"rx_data_slow_end_times_{x_axis_type}.txt"
    else:
        print("Invalid scenario number!")
        time_file = f"{scenario}_start_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)

    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{x_axis_val},{end_time},{image_size}\n")


if __name__ == "__main__":
    output_file, scenario, input_file, xtype = handle_CLI()

    if xtype == "loss":
        loss_list = LOSS_RANGE
        window_list = WINDOW_SIZE_FIXED
        timeout_list = TIMEOUT_FIXED
        x_axis_val = loss_list
    elif xtype == "window":
        loss_list = LOSS_FIXED
        window_list = WINDOW_SIZE_RANGE
        timeout_list = TIMEOUT_FIXED
        x_axis_val = window_list
    elif xtype == "timeout":
        loss_list = LOSS_FIXED
        window_list = WINDOW_SIZE_FIXED
        timeout_list = TIMEOUT_RANGE
        x_axis_val = timeout_list
    else:
        print("Unknown xtype. Must be either 'loss', 'window', or 'timeout'")
        exit(1)


    # Iterate over one of various variables, could be scenario loss, window size or timeout value
    x_idx = -1
    for loss in loss_list:
        for window_size in window_list:
            for timeout in timeout_list:
                x_idx += 1
                for iter in range(0, NUM_ITER):
                    print(
                        f"[{datetime.now().strftime('%S.%f')}] Scene {scenario}\t\t{xtype.capitalize()} {x_axis_val[x_idx]}%  \tIter {iter}"
                    )

                    image_bytes, end_time = receive_image(scenario, loss / 100)

                    if not check_image(image_bytes, input_file):
                        print("Received image does not match the original image!")
                        exit()

                    write_time_file(scenario, iter, x_axis_val[x_idx], xtype, end_time, len(image_bytes))

                    save_bmp(image_bytes, f"{output_file}")
