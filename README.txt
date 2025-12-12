========================
Title and Authors
========================

Phase: 5
Authors: Kevin Naranjo

========================
Environment
========================

OS: Ubuntu 22.04 (Through WSL)
Language & Version: Python 3.10.12
Extra packages: matplotlib

========================
File descriptions
========================

tcp_receiver.py: Contains the class that implements the TCP receiver protocol w/ options for adding packet errors
tcp_sender.py: Contains the class that implements the TCP sender protocol w/ options for adding packet errors
sender_app.py: Uses the TCP protocol to send an image to a listening application, does multiple iterations for each loss step from 0 to 70 percent
receiver_app.py: Uses the TCP protocol to receive an image from a sending application, does multiple iterations for each loss step from 0 to 70 percent
Packets.py: Contains data classes for generic Packet class, Data Packet class, and ACK Packet class, Fin Packet, SYN Packet, SYNACK packet
checksum.py: Contains functions for generating and validating a 16-bit XOR checksum
constants.py: Location for common constants used by multiple files
generate_timing_plots: Uses the time text files in results folder to generate timing and throughput analysis plots

data/megamind.bmp: 890 KB BMP test image

========================
Instructions
========================


---------------------------
Running the image transfer
---------------------------

1. Open two terminals, going forward these will be called T1 and T2. 

2. In T1, start the receiver application. You can specify the name you want to save the file as. If not name specified it will default to rx_img. You can also specify the data transfer scenario. 1 is no loss, 2 is ack loss, 3 is data loss, 4 is complete ACK drop, 5 is complete data drop.  To do the congesting window/timeout analysis pass in the -p flag.

    python3 receiver_app.py -o rx_test_image -s 1 -p

3. In T2, start the sender application. You can specify the name of the file you want to transmit. The data folder includes one test image, by default it will use this one. You can also specify the data transfer scenario in the same way as step 2. Must also use the -p flag if doing the window/RTT analysis. Can be specifiy the congestion window type with the -c flag. The options are 1 for slow start, 2 for AIMD, 3 for tcp tahoe, and 4 for tcp reno.

    python3 sender_app.py -i megamind -s 1 -c 3 -p

4. The sender and receiver will transfer the image a number of times specified by NUM_ITER in the constants.py file for each data step, the values iterated over are also specified in the constants.py file. If you specify the -p flag it will only do one iteration at 20% loss.

5. All the resulting images will be saved to the data folder.

6. Additionally, if the -p flag is used the plots for the window and timeout analysis are stored in the results folder.


---------------------------
Generating timing analysis plots
---------------------------

1. Once a transfer scenario has been run, it should be produce a start times file and an end times file in the results folder.

2. Run the plot generation script to analyze the times and generate data vs completion time plots for a specified scenario. You can specify which scenario to plot with command line argument, 1 is no loss, 2 is ack loss, 3 is data loss, 4 is complete ACK drop, 5 is complete data drop. 

   python3 generate_timing_plots.py -s 1

3. The resulting plot will be saved to the results folder for viewing. 