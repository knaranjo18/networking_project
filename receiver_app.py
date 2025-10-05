import argparse
import os

from constants import *
from rdt22_receiver import RDT22Receiver


def save_bmp(data: bytes, output_name: str):
    """Save an array of bytes to a BMP file on disk"""

    # Get image path
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    full_img_path = os.path.join(data_folder, output_name)

    print(f"Saving image to: {full_img_path}.bmp")

    # Write the image to file
    with open(f"{full_img_path}.bmp", "wb") as img_file:
        img_file.write(data)


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument(
        "-o", "--output_file", default="rx_img", help="The name to save the image as (no extension)"
    )
    parser.add_argument("-s", "--scenario", default=1, help="Data transfer scenario to implement")

    args = parser.parse_args()

    return args.output_file, args.scenario


if __name__ == "__main__":
    output_file, scenario = handle_CLI()
