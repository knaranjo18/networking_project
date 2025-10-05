import argparse
import os

import matplotlib.pyplot as plt

from constants import *


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument("-s", "--scenario", default=1, type=int, help="Data transfer scenario to implement")

    args = parser.parse_args()

    return args.scenario


def read_times_and_loss(file_name: str) -> dict[int, dict[int, list[int]]]:
    """Read times and loss from a time file and extrac them into a dictionary"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    full_time_file_path = os.path.join(results_folder, file_name)

    time_loss_dict: dict[int, list[int]] = {}

    # Instantiate dictionary entries
    for loss_int in range(0, 61, 5):
        time_loss_dict[loss_int] = []

    # Extract the loss and time
    with open(full_time_file_path, "r") as f:
        for line in f:
            _, loss, time = map(int, line.strip().split(","))
            time_loss_dict[loss].append(time)

    return time_loss_dict


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


def plot_time_loss(title: str, time_diffs: dict[int, int]):
    """Plots the loss vs completion time and saves it to file"""
    results_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    file_name = f"{title}_plot.png"
    full_path = os.path.join(results_folder, file_name)

    loss_axis = []
    time_axis = []

    for loss_int in range(0, 61, 5):
        try:
            time_axis.append(time_diffs[loss_int])
            loss_axis.append(loss_int)
        except:
            pass

    plt.plot(loss_axis, time_axis)
    plt.grid()
    plt.xlabel("Loss percentage")
    plt.ylabel("Average completion time (s)")
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
    else:
        print("Unknown scenario. Valid options are 1, 2, and 3")
        exit()

    start_times_loss = read_times_and_loss(f"{file_name}_start_times.txt")
    end_times_loss = read_times_and_loss(f"{file_name}_end_times.txt")

    avg_diffs_dict = get_time_diffs(start_times_loss, end_times_loss)

    plot_time_loss(file_name, avg_diffs_dict)
