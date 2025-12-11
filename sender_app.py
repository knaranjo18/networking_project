import argparse
import os
import socket as soc
import time
from datetime import datetime

from constants import *
from Packets import DataPacket
from tcp_sender import TCPSender
import matplotlib.pyplot as plt

def make_data_pkt(data: bytes) -> list[DataPacket]:
    """Helper function that takes an array of bytes and converts it to a list of Data Packets."""

    num_bytes = len(data)

    # Doing integer division to get the number of full packets
    num_full_pkts = num_bytes // MAX_DATA_SIZE

    pkt_list = []

    seq_num = 2

    # Extract the amount of data required per packet
    for i in range(num_full_pkts):
        curr_pkt =  DataPacket(data[i * MAX_DATA_SIZE : (i + 1) * MAX_DATA_SIZE], seq_num, src_port=TX_PORT, dst_port=RX_PORT)
        pkt_list.append(curr_pkt)
        seq_num += curr_pkt.data_len

    # Add the last packet with padding to get the full size
    pkt_list.append(DataPacket(data[num_full_pkts * MAX_DATA_SIZE :], seq_num, src_port=TX_PORT, dst_port=RX_PORT))

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

    parser.add_argument("-c", "--congest_control", default=1, type=int, help="Congestion control type")

    parser.add_argument("-p", "--plot_single_run", action="store_true", default=False, help="Plot one run at 20% to see congestion and timeout")


    args = parser.parse_args()

    return args.input_file, args.scenario, args.congest_control, args.plot_single_run


def send_image(bytes_image: bytes, scenario: int, loss: float, congest_control: int, plotting: bool) -> float:
    """Main loop that uses RDT 2.2 to send bytes to receiver"""

    # Create socket that will be used to send all packets
    tx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
    tx_soc.bind((TX_ADDR, TX_PORT))
    with tx_soc:
        # (Minimal change) Removed UDP connect; rdt4_sender uses recvfrom() for ACKs

        data_packet_list = make_data_pkt(bytes_image)

        sender = TCPSender(tx_soc, scenario, loss, congest_control)

        data_idx = 0

        start_time = time.time()

        sender.establish_connection()

        # Sends all data packets
        while data_idx < len(data_packet_list):
            while data_idx < len(data_packet_list) and sender.tcp_send(data_packet_list[data_idx]):
                if DEBUG_PRINT:
                    print(f"[{datetime.now().strftime('%S.%f')}] Sent packet with seq # {data_packet_list[data_idx].seq_num}")
                data_idx += 1
            sender.input(last_acks=False)

        # Ensure all packets are ACKed before finishing
        while not sender.input(last_acks=True):
            pass

        sender.close_connection()

        if plotting:
            if scenario == NO_LOSS:
                scene_name = f"no loss"
            elif scenario == TX_ACK_LOSS:
                scene_name = f"tx ack loss"
            elif scenario == RX_DATA_LOSS:
                scene_name = f"rx data loss"
            elif scenario == TX_ACK_DROP:
                scene_name = f"tx ack drop"
            elif scenario == RX_DATA_DROP:
                scene_name = f"rx data drop"

            if congest_control == SLOW_START:
                congest_name = "slow start"
            elif congest_control == AIMD:
                congest_name = "AIMD"
            elif congest_control == RENO:
                congest_name = "TCP Reno"
            elif congest_control == TAHOE:
                congest_name = "TCP Tahoe"

            x_axis = []
            y_axis = []
            for x, y in sender.sampRTT_list:
                x_axis.append(x)
                y_axis.append(y/1e-3)

            plt.figure(figsize=(10, 6))
            plt.plot(x_axis, y_axis)
            plt.xlabel("Simulation Time (s)")
            plt.ylabel("Time (ms)")
            
            x_axis = []
            y_axis = []
            for x, y in sender.timeout_list:
                x_axis.append(x)
                y_axis.append(y/1e-3)

            plt.plot(x_axis, y_axis)
            plt.title(f"Round Trip Time and Timeout\nScenario: {scene_name}\nCongestion strategy: {congest_name}")
            plt.legend(["Sample RTT", "Retransmission Timeout"])

            results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
            file_name = f"RTO_RTT_{scene_name}_{congest_name}.png"
            full_path = os.path.join(results_folder, file_name)

            plt.grid()
            plt.savefig(full_path)
            plt.close()


            x_axis = []
            y_axis = []
            for x, y in sender.cwnd_list:
                x_axis.append(x)
                y_axis.append(y)


            plt.figure(figsize=(10, 6))
            plt.plot(x_axis, y_axis)
            plt.ylabel("Window size (bytes)")
            plt.xlabel("Simulation Time (s)")
            plt.title(f"Congestion Window Size\nScenario: {scene_name}\nCongestion strategy: {congest_name}")
            plt.grid()
            plt.savefig(os.path.join(results_folder, f"cwin_{scene_name}_{congest_name}.png"))


            plt.figure(figsize=(10, 6))
            plt.plot(x_axis[0:200], y_axis[0:200], '-o')
            plt.ylabel("Window size (bytes)")
            plt.xlabel("Simulation Time (s)")
            plt.title(f"Congestion Window Size Zoomed\nScenario: {scene_name}\nCongestion strategy: {congest_name}")
            plt.grid()
            plt.savefig(os.path.join(results_folder, f"cwin_zoom_{scene_name}_{congest_name}.png"))



        return start_time


def write_time_file(
    scenario: int, iter: int, x_axis_val: int, x_axis_type:int, start_time: float, data_length: float
) -> None:
    """Write start time to file for later analysis"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_folder, exist_ok=True)  # <-- ensure folder exists

    if scenario == NO_LOSS:
        time_file = f"no_loss_start_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_LOSS:
        time_file = f"tx_ack_loss_start_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_LOSS:
        time_file = f"rx_data_loss_start_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_DROP:
        time_file = f"tx_ack_drop_start_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_DROP:
        time_file = f"rx_data_drop_start_times_{x_axis_type}.txt"
    elif scenario == TX_ACK_SLOW:
        time_file = f"tx_ack_slow_start_times_{x_axis_type}.txt"
    elif scenario == RX_DATA_SLOW:
        time_file = f"rx_data_slow_start_times_{x_axis_type}.txt"
    else:
        print("Invalid scenario number!")
        time_file = f"{scenario}_start_times.txt"

    full_time_file_path = os.path.join(results_folder, time_file)

    with open(full_time_file_path, "a") as f:
        f.write(f"{iter},{x_axis_val},{start_time},{data_length}\n")


if __name__ == "__main__":
    # Process command line arguments
    input_file, scenario, congest_control, plot_single_run = handle_CLI()

    bytes_image = image_file_2_bytes(input_file)

    if not plot_single_run:
        loss_list = LOSS_RANGE
        iter_num = NUM_ITER
    else:
        loss_list = LOSS_FIXED
        iter_num = 1

    x_axis_val = loss_list

    xtype = "loss"

    # Iterate over loss rate between 0 to 70 percent with increments of 5
    x_idx = -1
    for loss in loss_list:
        x_idx += 1
        for iter in range(0, iter_num):
            print(
                f"[{datetime.now().strftime('%S.%f')}] Scene {scenario}\t\t{xtype.capitalize()} {x_axis_val[x_idx]}%  \tIter {iter}"
            )
            start_time = send_image(bytes_image, scenario, loss / 100, congest_control, plot_single_run)
            write_time_file(scenario, iter, x_axis_val[x_idx], xtype, start_time, len(bytes_image))
            time.sleep(0.15)  # Wait a second between steps for things to settle
