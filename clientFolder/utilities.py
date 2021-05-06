import hashlib
MAXSEQSIZE = 10000000


def Create_File_Gen(file_name):
    with open(file_name, 'rb') as in_file:
        chunk = in_file.read(4096)
        yield chunk
        while len(chunk) > 0:
            chunk = in_file.read(4096)
            yield chunk

def incrementSeqNum(seq):
    if(type(seq) == type(b'')):
        seqInt = int.from_bytes(seq, byteorder='big')
    else:
        seqInt = seq
    seqInt += 1
    if(seqInt / MAXSEQSIZE >= 1):
        seqInt = 0
    return seqInt

def prepareStr(x):
    if x < 10:
        return "0" + str(x)
    else:
        return str(x)

def decode3WayResponse(packt):
    ack = int.from_bytes((packt[:3]), byteorder='big')
    seq = int.from_bytes((packt[-3:]), byteorder='big')
    return seq, ack

def decodePacket(packt):
    #packetStr = packt.decode('utf8')
    seq = int.from_bytes(packt[:3], byteorder='big')
    dataSize = int.from_bytes(packt[3:5], byteorder='big')
    checksum = packt[5:37].decode('utf8')
    flag = int(packt[37:39].decode('utf8'))
    data = packt[39:]
    return seq, dataSize, checksum, flag, data

def getFileData(flag, data):
    dataStr = data.decode('utf8')
    fileSize = int(dataStr[:flag])
    fileName = dataStr[flag:]
    return fileSize, fileName


def getFirstPacket(fileSize, fileName, seq):
    flag = len(str(fileSize))
    flagStr = prepareStr(flag)
    data = str(fileSize) + fileName
    dataSize = len(data)
    checksum = hashlib.md5(data.encode('utf8')).hexdigest()
    packetStr = checksum + flagStr + data
    return seq.to_bytes(3, byteorder='big') + dataSize.to_bytes(2, byteorder='big') + packetStr.encode('utf8')

def getPacket(data, seq):
    flagStr = '00'
    dataSize = len(data)
    checksum = hashlib.md5(data).hexdigest()
    packetStr = checksum + flagStr
    return (seq.to_bytes(3, byteorder='big') + dataSize.to_bytes(2, byteorder='big') + packetStr.encode('utf8')  + data)
