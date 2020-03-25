import argparse
import socket
import datetime
import time
import re

# Variable "declaration" section
archiveFreq = 5  # Default archive frequency in seconds
runTime = 60  # Default run time in minues
logging = False  # Default to no logging
PORT = 5005  # TCP port for connection to server
accumulatedTime = 0  # Counter to hold total run time
f = ''  # file object
data = ''  # Return string from server
cTime = ''
cDate = ''
depth = 0.0
depthFt = 0.0

# Function to validate IPv4 address
def validIp(Ip):
    # Create regular expression used to evaluate ipv4 address
    regexIp = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

    if (re.search(regexIp, Ip)):
        return (1)  # IP address is properly formed
    else:
        return (0)  # IP address is malformed


# Set up argument parser
parser = argparse.ArgumentParser(description='Python script to query a remote server for temperature and pressure\
 data, and optionally write that data to a text file.')
parser.add_argument("serverIP", help="IP Number of server")
parser.add_argument("-l", "--log", help="File name for logging (default is NO logging)")
parser.add_argument("-f", "--freq", help="Frequency (in secs) to read data [default " + str(archiveFreq) + " sec]", \
                    type=int)
parser.add_argument("-t", "--time", help="Time (in mins) to run [default " + str(runTime) + " min ]. -1 denotes run\
 forever.", type=int)

# Read arguments passed on command line
args = parser.parse_args()
fname = ''  # filename to log to

# Parse command line arguments
serverAddr = args.serverIP  # Server IP # - not optional
if not (validIp(serverAddr)):
    print(("Ip address " + serverAddr + " invalid. Exiting"))
    exit(-1)
if args.log:  # Log filename - optional
    fname = args.log
    logging = True
if args.freq:  # Read frequency - optional (default defined above)
    archiveFreq = args.freq
    if archiveFreq <= 0:
        print(("Invalid collection frequency (" + str(archiveFreq) + "). Exiting."))
        exit(-1)
if args.time:  # Run duration - optional (default defined above)
    runTime = args.time

# Display summary of command on console
print(("Connecting to server at :" + serverAddr))
if logging:
    # Open the file and write the header
    f = open(fname, 'a')
    f.write("Date Time,Press(mBar),Temp(c),Depth(m)\n")
else:
    print("Not logging to a file")
print(("Reading data every " + str(archiveFreq) + " seconds"))

# Write status to console
print("Starting pressure and temperature log with the following parameters:")
if logging:
    print(("Saving to file     : " + fname))
print(("Server IP#         : " + serverAddr))
print(("Logging frequency  : " + str(archiveFreq) + " seconds"))
if runTime <= 0:
    print("Acquiring data until stopped via user interrupt (ctrl-c)")
else:
    print(("Acquiring data for : " + str(runTime) + " minutes"))
currentDT = datetime.datetime.now()
print("")  # blank line
print(("Acquisition started : " + str(currentDT.strftime("%Y%m%d")) + " at " + str(currentDT.strftime("%H:%M:%S"))))
print("---------------------")

# Main loop
while True:
    try:
        if logging:
            f = open(fname, 'a')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)  # Set timeout for no response from server
        s.connect((serverAddr, PORT))
        currentDT = datetime.datetime.now()
        data = s.recv(1024)
        # populate list with elements of pressure, temperature
        elem = data.split(b',')  # type : List[str]
        depth = elem[2]
        depthFt = float(depth) * 3.28084
        cDate = str(currentDT.strftime("%Y%m%d"))
        cTime = str(currentDT.strftime("%H:%M:%S"))
        dataLine = cDate + ' ' + cTime + ',' + data.decode("utf-8")
        if logging:
            f.write(dataLine + '\n')
        print(("Server reports : " + data.decode("utf-8") + " at " + cTime + "(" + cDate + ")"))
        if runTime <= 0:
            print(("Run time       : " + str(accumulatedTime) + " seconds"))
        else:
            print(("Run time       : " + str(accumulatedTime) + " of " + str(int(runTime) * 60) + " seconds"))
        print(("Current depth  : " + "{0:.2f}".format(float(depth)) + " meters (" + "{0:.2f}".format(
            depthFt) + " ft)\n"))
        if logging:
            f.close()
            s.close()
        time.sleep(float(archiveFreq))
        accumulatedTime = accumulatedTime + float(archiveFreq)
        if (runTime > 0) & (accumulatedTime > int(runTime) * 60):
            print("Acquisition complete")
            exit(0)
    except socket.timeout:
        print("ERR: Timeout waiting for server response")
    except KeyboardInterrupt:
        if logging:
            f.close()
            s.close()
        print("tpMonitor terminated via user interrupt")
        exit(0)
