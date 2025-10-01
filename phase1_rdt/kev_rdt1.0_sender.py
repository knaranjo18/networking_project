# Author: Kevin Naranjo
# This program implements the Reliable Data Transfer (RDT) 1.0 protocol
# to send a BMP image to another application that is receiving it.

import argparse
import os
import socket as soc
import time

from Packet import Packet


def make_pkt(data: bytes) -> list[Packet]:
    """Helper function that takes an array of bytes and converts it to a list of Packets."""

    num_bytes = len(data)

    # Doing integer division to get the number of full packets
    num_full_pkts = num_bytes // Packet.DATA_SIZE

    pkt_list = []

    # Extract the amount of data required per packet
    for i in range(num_full_pkts):
        pkt_list.append(Packet(data[i * Packet.DATA_SIZE : (i + 1) * Packet.DATA_SIZE]))

    # Add the last packet with padding to get the full size
    pkt_list.append(Packet(data[num_full_pkts * Packet.DATA_SIZE :]))

    return pkt_list


def rdt_send(data: bytes):
    """Takes a byte array and sends it via UDP to a listening application in the form of packets."""

    # Create socket that will be used to send all packets
    tx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)

    packets = make_pkt(data)

    # First packet sent will contain the number of data packets to follow
    num_packets_bytes = len(packets).to_bytes(8, "little")
    first_packet = Packet(num_packets_bytes)
    udt_send(first_packet, tx_soc)

    # Send the data packets
    for packet in packets:
        time.sleep(0.000001)  # Might get dropped if too fast
        udt_send(packet, tx_soc)

    print(f"Done sending {len(packets)} packets.")

    tx_soc.close()


def udt_send(packet: Packet, socket: soc.socket):
    """Uses a UDP socket to send a packet of data."""

    RX_NAME = "127.0.0.1"
    RX_PORT = 54321

    # Extracts the bytes from the packet object to send
    socket.sendto(packet.full_pkt, (RX_NAME, RX_PORT))


def image_file_2_bytes(image_file_name: str) -> bytes:
    """Reads an image from a filename and converts it to bytes"""

    # Get image path
    data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    full_img_path = os.path.join(data_folder, image_file_name)

    # Read in image and convert to bytes
    try:
        with open(f"{full_img_path}.bmp", "rb") as img_file:
            img_bytes = img_file.read()
    except:
        print(f"Could not find file: {full_img_path}.bmp\nExiting program!")
        exit()

    return img_bytes


def handle_CLI() -> str:
    "Reads command line arguments to get the input file name"

    parser = argparse.ArgumentParser(description="Image sender with RDT 1.0 protocol")

    parser.add_argument(
        "-i", "--input_file", default="megamind", help="The name of the image to send (no extension)"
    )

    args = parser.parse_args()

    return args.input_file


if __name__ == "__main__":
    img_name = handle_CLI()

    bytes_image = image_file_2_bytes(img_name)

    print(f"Sending image data length: {len(bytes_image)} bytes")

    rdt_send(bytes_image)
