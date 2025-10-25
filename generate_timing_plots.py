import argparse
import os

import matplotlib.pyplot as plt
from constants import *


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument(
        "-s",
        "--scenario",
        default=1,
        type=int,
        help="Data transfer scenario to implement",
    )

    args = parser.parse_args()

    return args.scenario


def read_times_and_loss(file_name: str) -> tuple[dict[int, dict[int, list[int]]], dict[int, dict[int, list[int]]]]:
    """Read times and loss from a time file and extrac them into a dictionary"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    full_time_file_path = os.path.join(results_folder, file_name)

    time_loss_dict: dict[int, list[int]] = {}
    data_size_dict: dict[int, list[int]] = {}

    # Instantiate dictionary entries
    for loss_int in range(0, 61, 5):
        time_loss_dict[loss_int] = []
        data_size_dict[loss_int] = []

    # Extract the loss and time
    with open(full_time_file_path, "r") as f:
        for line in f:
            try:
                _, loss, time, num_data_bytes = map(float, line.strip().split(","))
            except:
                _, loss, time = map(float, line.strip().split(","))
                num_data_bytes = 911934

            data_size_dict[loss].append(num_data_bytes)
            time_loss_dict[loss].append(time)

    return time_loss_dict, data_size_dict


def get_time_diffs(start_time_loss: dict[int, list], end_time_loss: dict[int, list]) -> dict[int, int]:
    """Given a start time dictionary and end time dictionary, calculate the average time difference for each loss level"""
    avg_diffs_dict = {}

    for loss_int in range(0, 61, 5):
        diff_list = []
        start_time_list = start_time_loss[loss_int]
        end_time_list = end_time_loss[loss_int]

        # Calculate the time difference for each iteration
        for iter in range(len(start_time_list)):
            diff_list.append(end_time_list[iter] - start_time_list[iter])

        # Calculate the average difference over the iterations
        if len(diff_list) != 0:
            avg_diffs_dict[loss_int] = sum(diff_list) / len(diff_list)

    return avg_diffs_dict


def calc_throughput(avg_diffs_dict: dict[int, int], data_size_dict: dict[int, list[int]]) -> dict[int, int]:
    """Calculate the average throughput in Kilobits per second for each loss level"""

    throughput_dict = {}

    for loss_int in range(0, 61, 5):
        curr_time = avg_diffs_dict[loss_int]
        num_bits = (sum(data_size_dict[loss_int]) / len(data_size_dict[loss_int])) * 8

        if curr_time != 0:
            throughput_dict[loss_int] = num_bits / 1024 / 1024 / curr_time

    return throughput_dict


def general_plot(title: str, x_data_list, y_data_dict: dict[int, int], xlabel: str, ylabel: str, ylim: int):
    """General plotting function"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    file_name = f"{title}_plot.png"
    full_path = os.path.join(results_folder, file_name)

    x_axis = []
    y_axis = []

    for x in x_data_list:
        try:
            y_axis.append(y_data_dict[x])
            x_axis.append(x)
        except:
            pass

    print(x_axis)
    print(y_axis)

    plt.plot(x_axis, y_axis)
    plt.ylim(0, ylim)
    plt.grid()
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(f"Scenario: {title}")

    plt.savefig(full_path)


if __name__ == "__main__":
    scenario = handle_CLI()

    if scenario == NO_LOSS:
        file_name = "no_loss"
    elif scenario == TX_ACK_LOSS:
        file_name = "tx_ack_loss"
    elif scenario == RX_DATA_LOSS:
        file_name = "rx_data_loss"
    elif scenario == TX_ACK_DROP:
        file_name = "tx_ack_drop"
    elif scenario == RX_DATA_DROP:
        file_name = "rx_data_drop"
    else:
        print("Unknown scenario. Valid options are 1, 2, and 3, 4, 5")
        exit()

    start_times_loss, _ = read_times_and_loss(f"{file_name}_start_times.txt")
    end_times_loss, data_size_dict = read_times_and_loss(f"{file_name}_end_times.txt")

    avg_diffs_dict = get_time_diffs(start_times_loss, end_times_loss)
    avg_throughput = calc_throughput(avg_diffs_dict, data_size_dict)

    loss_list = list(range(0, 61, 5))

    general_plot(f"{file_name}_time", loss_list, avg_diffs_dict, "Loss percentage", "Average completion time (s)", 15)
    plt.close()
    general_plot(f"{file_name}_throughput", loss_list, avg_throughput, "Loss percentage", "Average throughput (Mbps)", 25)
