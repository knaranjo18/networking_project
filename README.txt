========================
Title and Authors
========================

Phase: 2
Authors: Kevin Naranjo, Cesar Guevara, Jesse Taube

========================
Environment
========================

OS: Ubuntu 22.04 (Through WSL)
Language & Version: Python 3.10.12

========================
File descriptions
========================

rdt22_receiver.py: Contains the class that implements the RDT2.2 receiver protocol w/ options for adding packet errors
rdt22_sender.py: Contains the class that implements the RDT2.2 sender protocol w/ options for adding packet errors
sender_app.py: Uses the RDT 2.2 protocol to send an image to a listening application
receiver_app.py: Uses the RDT 2.2 protocol to receive an image from a sending application
Packets.py: Contains data classes for generic Packet class, Data Packet class, and ACK Packet class
checksum.py: Contains functions for generating and validating a 16-bit XOR checksum

checksum_test.py: Test script to verify functionality of checksum functions
packet_test.py: Test script to verify that functionality of Packet classes.

========================
Instructions
========================

1. Open two terminals, going forward these will be called t1 and t2. 

2. In t1 