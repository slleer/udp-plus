import time
from socket import *
import os
import utilities
import sys
import hashlib

# used in comparing sequnce and acknowledgement numbers, the range of these numbers
# is from 0 - 9999999. These numbers must be no more then 7 characters long.
MINSEQVAL = 0
MAXSEQVAL = 9999999
END = False # control variable used to determine if server has recieved the last packet

fileName = ""
fileSize = 0
# Create a UDP socket
serverSocket = socket(AF_INET, SOCK_DGRAM)
#instantiate the ACK value
ACK = int((str(format(time.time(), '.7f')))[-7:])

client_seq_num = 0
# Assign IP address and port number to socket
serverSocket.bind(('', 12354))
# start recieving for three way handshake and store the sequence number first sent by client
packet, address = serverSocket.recvfrom(5000)
client_seq_num = utilities.incrementSeqNum(int.from_bytes(packet, byteorder='big'))
threeWayHandShake = True
# send first acknowledgement of three way handshake with ACK # and the next expected seq #
message = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
serverSocket.sendto(message, address)
print("Three way handshake acknowledged by server.")
# while loop used to control the rest of the three way handshake
while threeWayHandShake:
    serverSocket.settimeout(1) # timeout needed to ensure proper contol and flow

    try:
        # continue to recieve from client and send ack on matching of expected seq and ack #'s
        # this is expecting a second packet from client that is in excess of standared three way
        # handshake but is used as contorl mechanism
        response, addr = serverSocket.recvfrom(5000)
        seq, ack = utilities.decode3WayResponse(response)
        if((client_seq_num == seq) and (ACK+1 == ack or (MINSEQVAL == ack and ACK == MAXSEQVAL))):
            threeWayHandShake = False
            stillReceiving = True
            #ACK = utilities.incrementSeqNum(ACK)
            print("here")
        else:
            # send acknowledgement for expected packet because an incorrect packet was recieved
            serverSocket.sendto(message, address)


    #If data is not received from client by timeout, respond
    except timeout:
        # if the server timesout here, that means it has already sent the first acknowledgement
        # of the three way handshake and has timedout waiting for second extra acknowledgement
        if(ACK == 0): # left over code from when using a different approach.
            serverSocket.sendto(message, address)
        else: # necessary to terminate current loop and progress
            threeWayHandShake = False
            stillReceiving = True
            print("at the execpt else")
            #ACK = utilities.incrementSeqNum(ACK)

# while loop for handling the file transfer process
print("Server finished with three way handshake, ready to receive file from client.")
while stillReceiving:
    serverSocket.settimeout(1)
    try:
        # recieve packets from client unitl an packet with empty data value comes in
        response, addr = serverSocket.recvfrom(5000)
        seq, dataSize, checksum, flag, data = utilities.decodePacket(response)
        if(END):
            acknowledge = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
            serverSocket.sendto(acknowledge, address)

        if(client_seq_num == seq and address == addr):
            if(checksum == hashlib.md5(data).hexdigest() and dataSize == len(data)):
                if(flag <= 0): #the packet contains the contents of the file, add those contents to file
                    print("Packet recieved from client, sending acknowledgement.", dataSize)
                    with open(fileName, 'ab') as out_file:
                        out_file.write(data)
                else: # first packet containing the file name and size is recieved
                    print("File name and file size recieved from client, sending acknowledgement.")
                    fileSize, fileName = utilities.getFileData(flag, data)
                # acknowledge the most recent packet recieved
                ACK = utilities.incrementSeqNum(ACK)
                acknowledge = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
                client_seq_num = utilities.incrementSeqNum(client_seq_num)
                serverSocket.sendto(acknowledge, address)

                # end of file has been detected, use END as control to ensure that server continues to listen
                # in case final acknowledgement packet was lost in route
                if (dataSize == 0):
                    END = True
                    print("File finished being sent by client, final acknowledgement sent.")
            else:
                # reqest resending of data due to data corruption
                #-- checksum and/or dataSize do not match with data --
                print("Requesting packet to be resent by client due to corrupted data.")
                request = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
                serverSocket.sendto(request, address)
        else:
            # resends acknowledgement for last in order packet recieved, this can be due to revieving out
            # of order packet or if last acknowledgement packet was lost
            print("Requesting packet to be resent by client or resending acknowledgement per request from client.")
            request = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
            serverSocket.sendto(request, address)

    except timeout:
        # control flow block to break out of while loop if no request is made from client
        # to resend final acknowledgement packet
        if(END):
            stillReceiving = False
            continue
        # resend most recent acknowledgement due to server timeout waiting for response from client
        print("Resending acknowledgement to client for last recieved packet due to timeout.")
        request = ACK.to_bytes(3, byteorder='big') + client_seq_num.to_bytes(3, byteorder='big')
        serverSocket.sendto(request, address)

# close connection when complete
serverSocket.close()
# compare file size sent as packet and filesize of created file
if(fileSize == os.stat(fileName).st_size):
    print("The size of the file recieved through UDP matches the size that was sent from the client.")
else:
    print("The size of the file recieved through UDP does not match the size sent by the client")

# begin tcp connection to recieve same file to compare with file recieved by udp.
print("Strating tcp connection from server for verification.")
with socket(AF_INET, SOCK_STREAM) as stcp:
    stcp.bind(('', 12354))
    stcp.listen()
    conn, addr = stcp.accept()
    with conn:
        print("TCP server connnected to client.")
        while True:
            # recieve from client until empty data packet is returned.
            packet = conn.recv(5000)
            if not packet:
                break
            seq, dataSize, checksum, flag, data = utilities.decodePacket(packet)
            if(flag <= 0): # file contents are being recieved and added to file
                with open(fileName_TCP, 'ab') as tcp_out:
                    tcp_out.write(data)
            else: # file name and size are recieved as first packet
                fileSize_TCP, fileName_TCP = utilities.getFileData(flag, data)
                fileName_TCP = "TCP" + fileName_TCP

#finished file transher from tcp, compare size of each file and size value sent from as packet by each method
print("File finished being recieved via tcp from client.")
if(fileSize_TCP == os.stat(fileName_TCP).st_size and os.stat(fileName).st_size == fileSize):
    print("The size of the file sent over UDP matches the size of the file sent over tcp.")
else:
    print("The size of the file sent over UDP does not matcht the size of the file sent over tcp.")
