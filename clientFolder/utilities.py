import hashlib
# this is a helper module used to hold many needed functions for both the client and server

# used in putting a cap on the sequence and acknowledgement numbers so they
# are always 7 digits
MAXSEQSIZE = 10000000

# A generator function for iterating over the file contents with minimal impact on memory
# this is used to read chunks of file no larger then 4096 characters long
def Create_File_Gen(file_name):
    with open(file_name, 'rb') as in_file:
        chunk = in_file.read(4096)
        yield chunk
        while len(chunk) > 0:
            chunk = in_file.read(4096)
            yield chunk

# a function used to increment both sequence and acknowledgement numbers while ensuring
# the remain only seven digits long
def incrementSeqNum(seq):
    if(type(seq) == type(b'')):
        seqInt = int.from_bytes(seq, byteorder='big')
    else:
        seqInt = seq
    seqInt += 1
    if(seqInt / MAXSEQSIZE >= 1):
        seqInt = 0
    return seqInt

# a helper function used to return a two character string representation of a number
def prepareStr(x):
    if x < 10:
        return "0" + str(x)
    else:
        return str(x)

# method for decoding the response from the client, originally only used for the
# three way handshake, it is now used for all acknowledgements from server
def decode3WayResponse(packt):
    ack = int.from_bytes((packt[:3]), byteorder='big')
    seq = int.from_bytes((packt[-3:]), byteorder='big')
    return seq, ack

# decode the packet and return the individual parts for packet validation and data processing
def decodePacket(packt):
    #packetStr = packt.decode('utf8')
    seq = int.from_bytes(packt[:3], byteorder='big')
    dataSize = int.from_bytes(packt[3:5], byteorder='big')
    checksum = packt[5:37].decode('utf8')
    flag = int(packt[37:39].decode('utf8'))
    data = packt[39:]
    return seq, dataSize, checksum, flag, data

# used to separate the file name and size from each other and return their individual values
# using flag value passed with packet as the slicing position
def getFileData(flag, data):
    dataStr = data.decode('utf8')
    fileSize = int(dataStr[:flag])
    fileName = dataStr[flag:]
    return fileSize, fileName

# this function creates the first packet, using a flag vaiable to inform the server where the
# file size ends and name begins in the data portion of the packet.
def getFirstPacket(fileSize, fileName, seq):
    flag = len(str(fileSize))
    flagStr = prepareStr(flag)
    data = str(fileSize) + fileName
    dataSize = len(data)
    checksum = hashlib.md5(data.encode('utf8')).hexdigest()
    packetStr = checksum + flagStr + data
    return seq.to_bytes(3, byteorder='big') + dataSize.to_bytes(2, byteorder='big') + packetStr.encode('utf8')

# this function is used to create all packets after the first. All packets are constructed with
# 3byte sequence number, 2byte dataSize (enforced by the chunk size of the generator function)
# 32byte checksum (hash of the data), 2byte flag, and data.
def getPacket(data, seq):
    flagStr = '00'
    dataSize = len(data)
    checksum = hashlib.md5(data).hexdigest()
    packetStr = checksum + flagStr
    return (seq.to_bytes(3, byteorder='big') + dataSize.to_bytes(2, byteorder='big') + packetStr.encode('utf8')  + data)
