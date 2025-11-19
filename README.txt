========================
Title and Authors
========================

Phase: 4
Authors: Kevin Naranjo, Jesse Taube

========================
Environment
========================

OS: Ubuntu 22.04 (Through WSL)
Language & Version: Python 3.10.12
Extra packages: matplotlib

========================
File descriptions
========================

rdt4_receiver.py: Contains the class that implements the RDT4.0 receiver protocol w/ options for adding packet errors
rdt4_sender.py: Contains the class that implements the RDT4.0 sender protocol w/ options for adding packet errors
sender_app.py: Uses the RDT 4.0 protocol to send an image to a listening application, does multiple iterations for each loss step from 0 to 60 percent or window size or timeout
receiver_app.py: Uses the RDT 4.0 protocol to receive an image from a sending application, does multiple iterations for each loss step from 0 to 60 percent or window size or timeout
Packets.py: Contains data classes for generic Packet class, Data Packet class, and ACK Packet class
checksum.py: Contains functions for generating and validating a 16-bit XOR checksum
constants.py: Location for common constants used by multiple files
generate_timing_plots: Uses the time text files in results folder to generate timing and throughput analysis plots

checksum_test.py: Test script to verify functionality of checksum functions
packet_test.py: Test script to verify that functionality of Packet classes.

data/megamind.bmp: 890 KB BMP test image

========================
Instructions
========================


---------------------------
Running the image transfer
---------------------------

1. Open two terminals, going forward these will be called T1 and T2. 

2. In T1, start the receiver application. You can specify the name you want to save the file as. If not name specified it will default to rx_img. You can also specify the data transfer scenario. 1 is no loss, 2 is ack loss, 3 is data loss, 4 is complete ACK drop, 5 is complete data drop. Can also specify what you want to iterate over. Can be "loss", "timeout", or "window". 

    python3 receiver_app.py -o rx_test_image -s 1 -x loss

3. In T2, start the sender application. You can specify the name of the file you want to transmit. The data folder includes one test image, by default it will use this one. You can also specify the data transfer scenario and iteration type in the same way as step 2.

    python3 sender_app.py -i megamind -s 1 -x loss

4. The sender and receiver will transfer the image a number of times specified by NUM_ITER in the constants.py file for each data step, the values iterated over are also specified in the constants.py file.

5. All the resulting images will be saved to the data folder.


---------------------------
Generating timing analysis plots
---------------------------

1. Once a transfer scenario has been run, it should be produce a start times file and an end times file in the results folder.

2. Run the plot generation script to analyze the times and generate data vs completion time plots for a specified scenario. You can specify which scenario to plot with command line argument, 1 is no loss, 2 is ack loss, 3 is data loss, 4 is complete ACK drop, 5 is complete data drop. You must also specify Can also specify the data to plot on the x-axis. Can be "loss", "timeout", or "window". 

   python3 generate_timing_plots.py -s 1 -x loss

3. The resulting plot will be saved to the results folder for viewing. 