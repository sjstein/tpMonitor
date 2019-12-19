# Streaming Client
import socket
import datetime
import time
import sys
# Read config file
from configobj import ConfigObj

# Open and read configuration file

config = ConfigObj('tpMonitor.ini')
DELAY = config['timeSlice']
RUNTIME = config['runTime']
HOST = config['serverIP']

# TCP port for connection to server
PORT = 5005

# Check for proper number of arguments.
nbrArgs = len(sys.argv) - 1
if nbrArgs < 1:
    print "Usage: " + sys.argv[0] + " <fname>  Where <fname> is the file used to store the data."
    print "NOTE    : If <fname> already exists, new data will be appended to it."
    print "NOTE(2) :" + sys.argv[0] + " expects the init file 'tpMonitor.ini' within the root directory"
    exit(1)

# Open the file and write the header
f = open(sys.argv[1], 'a')
f.write("Date Time,Press(mBar),Temp(c),Depth(m)\n")

# Write status to console
print("Starting pressure and temperature log with the following parameters:")
print("Saving to file     : " + sys.argv[1])
print("Server IP#         : " + HOST)
print("Polling frequency  : " + DELAY + " seconds")
print("Acquiring data for : " + RUNTIME + " minutes")
currentDT = datetime.datetime.now()
print  # blank line
print("Acquisition started :" + str(currentDT.strftime("%Y%m%d")) + " at " + str(currentDT.strftime("%H:%M:%S")))

accumulatedTime = 0  # Variable to hold how much time we have been running

while True:
    f = open(sys.argv[1], 'a')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    currentDT = datetime.datetime.now()
    data = s.recv(1024)

    # populate list with elements of pressure, temperature
    elem = data.split(",")  # type: List[str]
    depth = elem[2]
    cDate = str(currentDT.strftime("%Y%m%d"))
    cTime = str(currentDT.strftime("%H:%M:%S"))
    dataLine = cDate + ' ' + cTime + ',' + str(data)
    f.write(dataLine + '\n')
    f.close()
    s.close()
    time.sleep(float(DELAY))
    accumulatedTime = accumulatedTime + int(DELAY)
    if accumulatedTime > int(RUNTIME) * 60:
        print("Acquisition complete")
        exit(0)
    print("Server reports : " + data + " at " + cTime + "(" + cDate + ")")
    print("Run time       : " + str(accumulatedTime) + " of " + str(int(RUNTIME) * 60) + " seconds")
    print("Current depth  : " + depth + " meters\n")
