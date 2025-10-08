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


1. Open two terminals, going forward these will be called T1 and T2.

2. In T1 (Receiver side):
   Start the receiver application. You can specify the output file name and the transfer scenario.
   - If no name is specified, it defaults to rx_img.
   - The -s flag controls the test scenario:
     - 1 = No loss
     - 2 = ACK loss
     - 3 = DATA loss

   Example:
   ```bash
   python3 receiver_app.py -o rx_test_image -s 1
   ```

   - Scenario 1 (No loss): Receiver and sender exchange packets normally with no simulated network loss.
   - Scenario 2 (ACK loss): The receiver will randomly drop acknowledgment (ACK) packets based on the configured loss rate in constants.py. This tests sender retransmission behavior when ACKs are lost.
   - Scenario 3 (DATA loss): The receiver simulates data packet loss, forcing retransmissions from the sender when expected sequence numbers are not received.

3. In T2 (Sender side):
   Start the sender application. You can specify the input image file and the same scenario number.
   - By default, it will use the test image located in the data folder (megamind.png or similar).

   Example:
   ```bash
   python3 rdt1.0_sender.py -i megamind -s 1
   ```

   Replace -s 1 with -s 2 or -s 3 to match the scenario chosen on the receiver side.

4. The sender and receiver will transfer the image multiple times as defined by NUM_ITER in constants.py, for each simulated loss percentage (from 0% to 60% in steps of 5%).

5. All received images will be saved automatically in the data/ directory.
   Each test run will include log output showing sequence numbers, retransmissions, and loss simulation results, helping visualize reliability performance across different loss conditions.



---------------------------
Generating timing analysis plots
---------------------------

1. Once a transfer scenario has been run, it should be produce a start times file and an end times file in the results folder.

2. Run the plot generation script to analyze the times and generate loss vs completion time plots for a specified scenario. You can specify which scenario to plot with command line argument, 1 is no loss, 2 is ack loss, and 3 is data loss. 

   python3 generate_timing_plots -s 1

3. The resulting plot will be saved to the results folder for viewing. 
