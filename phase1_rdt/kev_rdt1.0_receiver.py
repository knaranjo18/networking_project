# Author: Kevin Naranjo
# This program implements the Reliable Data Transfer (RDT) 1.0 protocol
# to receive a BMP image from another application that is sending it. Once
# received it will display the image via the GUI.

import argparse
import os
import socket as soc

from Packet import Packet


def create_udp_soc() -> soc.socket:
    """Create a UDP socket to listen on a port"""

    RX_NAME = "127.0.0.1"
    RX_PORT = 54321

    rx_soc = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)

    rx_soc.bind((RX_NAME, RX_PORT))

    return rx_soc


def udt_rx(rx_soc: soc.socket) -> bytes:
    """Blocks until it receives a packet from the UDP socket"""

    rx_data, _ = rx_soc.recvfrom(1024)
    return rx_data


def rdt_rcv() -> bytes:
    """Listens for data on a UDP socket. The first packet is the total number of data packets expected. Then
    it receives packets until expected value is reached. After which it combines the data from the packets into
    a byte array."""

    # Create listening socket
    rx_soc = create_udp_soc()

    try:
        print("Waiting for initial packet")

        # Reads in the first packet to know how many packets of data to expect
        rx_data = udt_rx(rx_soc)
        first_packet = Packet.packet_from_bytes(rx_data)
        num_packets = int.from_bytes(first_packet.data, "little")
        print(f"Expecting {num_packets} packets")

        rx_packet_list = []

        # Receive until we get the number of expected packets
        for _ in range(num_packets):
            rx_data = udt_rx(rx_soc)
            rx_packet_list.append(Packet.packet_from_bytes(rx_data))

        print(f"Received {len(rx_packet_list)} packets")
    except KeyboardInterrupt:
        print("\nCtr+C detected. Shutting down server.")
        rx_soc.close()
        exit()

    rx_soc.close()

    # Return the complete data byte array
    return combine_packets(rx_packet_list)


def combine_packets(packet_list: list[Packet]) -> bytes:
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


def handle_CLI() -> str:
    "Reads command line arguments to get the output file name"

    parser = argparse.ArgumentParser(description="Image receiver with RDT 1.0 protocol")

    parser.add_argument(
        "-o", "--output_file", default="rx_img", help="The name to save the image as (no extension)"
    )

    args = parser.parse_args()

    return args.output_file


if __name__ == "__main__":
    output_file = handle_CLI()

    # Receive the image data
    bytes_image = rdt_rcv()

    print(f"Received image data length: {len(bytes_image)} bytes")

    # Save the image to disk
    save_bmp(bytes_image, output_file)
