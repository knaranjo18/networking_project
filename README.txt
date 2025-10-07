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
sender_app.py: Uses the RDT 2.2 protocol to send an image to a listening application, does multiple iterations for each loss step from 0 to 60 percent
receiver_app.py: Uses the RDT 2.2 protocol to receive an image from a sending application, does multiple iterations for each loss step from 0 to 60 percent
Packets.py: Contains data classes for generic Packet class, Data Packet class, and ACK Packet class
checksum.py: Contains functions for generating and validating a 16-bit XOR checksum
constants.py: Location for common constants used by multiple files
generate_timing_plots: Uses the time text files in results folder to generate timing analysis plots

checksum_test.py: Test script to verify functionality of checksum functions
packet_test.py: Test script to verify that functionality of Packet classes.

results/no_loss_start_times.txt: Text file containing start times for no loss scenario
results/no_loss_end_times.txt: Text file containing end times for no loss scenario
results/tx_ack_loss_start_times.txt: Text file containing start times for ACk loss scenario
results/tx_ack_loss_end_times.txt: Text file containing end times for ACk loss scenario
results/rx_data_loss_start_times.txt: Text file containing start times for data loss scenario
results/rx_data_loss_end_times.txt: Text file containing end times for data loss scenario

data/megamind.bmp: 890 KB BMP test image

========================
Instructions
========================


---------------------------
Running the image transfer
---------------------------

1. Open two terminals, going forward these will be called T1 and T2. 

2. In T1, start the receiver application. You can specify the name you want to save the file as. If not name specified it will default to rx_img. You can also specify the data transfer scenario. 1 is no loss, 2 is ack loss, and 3 is data loss. 

    python3 receiver_app.py -o rx_test_image -s 1

3. In T2, start the sender application. You can specify the name of the file you want to transmit. The data folder includes one test image, by default it will use this one. You can also specify the data transfer scenario in the same way as step 2. 

    python3 sender_app.py -i megamind -s 1

4. The sender and receiver will transfer the image a number of times specified by NUM_ITER in the constants.py file for each loss percentage step, these go from 0 to 60 with steps of 5. 

5. All the resulting images will be saved to the data folder.


---------------------------
Generating timing analysis plots
---------------------------

1. Once a transfer scenario has been run, it should be produce a start times file and an end times file in the results folder.

2. Run the plot generation script to analyze the times and generate loss vs completion time plots for a specified scenario. You can specify which scenario to plot with command line argument, 1 is no loss, 2 is ack loss, and 3 is data loss. 

   python3 generate_timing_plots -s 1

3. The resulting plot will be saved to the results folder for viewing. 