import time
from socket import *
import os
import utilities
import sys

# used in comparing sequnce and acknowledgement numbers, the range of these numbers
# is from 0 - 9999999. These numbers must be no more then 7 characters long.
MINSEQVAL = 0
MAXSEQVAL = 9999999
END = False # control variable used to determine if server has recieved the last packet
#create UDP socket
addr = ("127.0.0.1", 12354)
clientSocket = socket(AF_INET, SOCK_DGRAM)
client_seq_num = int((str(format(time.time(), '.7f')))[-7:]) # instatiate client_seq_num
print(client_seq_num, " seq")
ACK = 0
# send first message for three way handshake to server
message = client_seq_num.to_bytes(3, byteorder='big')
clientSocket.sendto(message, addr)
print("Three way handshake started by client.")
threeWayHandShake = True
stillReceiving = False
# while loop used for controling the reciept of the server acknowledgements for three way handshake
while threeWayHandShake:

    clientSocket.settimeout(1)
    try:
        # recieve acknowledgement from server, increment, and store ACK number to represent the next expected ACK
        response, server = clientSocket.recvfrom(5000)
        seq, ack = utilities.decode3WayResponse(response)
        if(client_seq_num+1 == seq or (MINSEQVAL == seq and client_seq_num == MAXSEQVAL)):
            if(not END):
                # on succesfull reciept of acknowledgement packet, send the next packet which is extra and used for
                # control during three way handshake
                client_seq_num = utilities.incrementSeqNum(client_seq_num)
                ACK = utilities.incrementSeqNum(response[:3])
                finalHandshake = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
                clientSocket.sendto(finalHandshake, server)
                print("Three way handshake server acknowledgement recieved by client.")
                END = True
            # control block used to ensure client is waiting for a response to extra handshake packet
            else:
                threeWayHandShake = False
                stillReceiving = True
                continue
        else:
            # send previous packet
            clientSocket.sendto(message, addr)


    #if timeout occurs
    except timeout:
        # first acknowledgement packet has not been recieved, resend first handshake packet
        if(ACK == 0):
            clientSocket.sendto(message, addr)
        # three way handshake is complete, timeout occured waiting for response to extra handshake packet
        else:
            #seq_num = seq_num + 1
            print("down here bro")
            threeWayHandShake = False
            stillReceiving = True




END = False # reset control block for reuse
# hardcoded filename, filesize is dynamic.
file_name = "message.txt"
file_size = os.stat(file_name).st_size
# call to generator creation object for use in iterating over file and creating and sending packets
file_gen = utilities.Create_File_Gen(file_name)
print("Client finished with three way handshake, ready to send file to server.")
# send first packet of the file transfer containing the file name and size for validation and file creation
message = utilities.getFirstPacket(file_size, file_name, client_seq_num)
clientSocket.sendto(message, addr)
print("File name and file size sent to server.")
# while loop used to control the reciept of acknowledgements and send the contents of the file
while stillReceiving:
    clientSocket.settimeout(1) # timeout needed to ensure proper control and flow
    try:
        #recieve server acknowledgement packets check to see if they match expected values
        response, server = clientSocket.recvfrom(5000)
        seq, ack = utilities.decode3WayResponse(response)
        if(ACK == ack):
            if(not END):
                # in order ack recieved, send next packet
                print("Acknowledgement received from server, sending next packet.")
                client_seq_num = utilities.incrementSeqNum(client_seq_num)
                ACK = utilities.incrementSeqNum(response[:3])
                data = next(file_gen) # call to generator function to get the next chunk of data from file
                message = utilities.getPacket(data, client_seq_num)
                clientSocket.sendto(message, server)

                # control flow block used to ensure client waits for final acknowledgement after sending
                # the final packet.
                if(len(data) == 0):
                    END = True
                    print("File finished sending to server, waiting for acknowledgement or timeout.")
            else: # control flow block
                stillReceiving = False
                continue
        else:
            # resend last message sent to server on reciept of incorrect/out of order acknowledgement
            clientSocket.sendto(message, addr)


    # handle timeouts if they occur during file transfer
    except timeout:
        # resend last packet sent on timeout
        clientSocket.sendto(message, addr)
        print("Timeout occurred, resending packet to server.")


# this sleep is needed to ensure the UDP connection doesn't close while the sesrver is still listening
# server listens after sending final acknowledgement in case of lost packet to resend if necessary
time.sleep(1)
clientSocket.close()
ENDTCP = False # tcp control block variable
print("File sent to server successfully through UDP.")
print("Starting tcp connection from client for verification.")
#star the tcp connection for file verification
with socket(AF_INET, SOCK_STREAM) as ctcp:
    ctcp.connect(("127.0.0.1", 12354))
    print("TCP connection established with server.")
    # prepare first packet, using same means as the above UDP, containing file name and size
    tcp_gen = utilities.Create_File_Gen(file_name)
    print("Sending file name and file size to sever via tcp.")
    tcp_message = utilities.getFirstPacket(file_size, file_name, client_seq_num)
    while not ENDTCP:
        # send first and all subsequent packets to server
        ctcp.sendall(tcp_message)
        data = next(tcp_gen)
        tcp_message = utilities.getPacket(data, client_seq_num)
        if(not data): # control block used to terminate connection when file finished sending.
            ENDTCP = True
            continue
# file has successfully been sent twice
print("File finished sending to server via tcp successfully.")
