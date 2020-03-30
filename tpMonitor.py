import argparse
import socket
import datetime
import time
import re
import sys

# Variable "declaration" section
archive_freq = 5  # Default archive frequency in seconds
run_time = 60  # Default run time in minues
logging = False  # Default to no logging
accum_time = 0  # Counter to hold total run time
f = ''  # file object
s = ''  # socket object
data = ''  # Return string from server
curr_time = ''
curr_date = ''
depth_meters = 0.0
depth_feet = 0.0
prog_name = '{' + sys.argv[0] + '}'
verbosity = 2

# Constants
PORT = 5005  # TCP port for connection to server
ERRO = 2  # Message types
WARN = 1
INFO = 0


# Function to validate IPv4 address
def valid_ip(ip_nbr):
    # Create regular expression used to evaluate ipv4 address
    regex_ip = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

    if (re.search(regex_ip, ip_nbr)):
        return (1)  # IP address is properly formed
    else:
        return (0)  # IP address is malformed


# Function to return a timestamp string
def timestamp():
    curr_date_time = datetime.datetime.now()
    curr_date = str(curr_date_time.strftime("%Y%m%d"))
    curr_time = str(curr_date_time.strftime("%H:%M:%S"))
    time_line = curr_date + ' ' + curr_time
    return (time_line)


# Function to print message on console
def console_message(msg: str, severity=3):
    print("verbosity = " + str(verbosity))
    if severity == ERRO:
        print((timestamp() + " [ERRO] " + msg + " " + prog_name))
    elif severity == WARN and verbosity > 0:
        print((timestamp() + " [WARN] " + msg + " " + prog_name))
    elif severity == INFO and verbosity > 1:
        print((timestamp() + " [INFO] " + msg + " " + prog_name))
    elif verbosity > 1:
        print(msg)
    return ()


# Set up argument parser
parser = argparse.ArgumentParser(description='Python script to query a remote server for temperature and pressure\
 data, and optionally write that data to a text file.')
parser.add_argument("serverIP", help="IP Number of server")
parser.add_argument("-l", "--log", help="File name for logging (default is NO logging)")
parser.add_argument("-f", "--freq", help="Frequency (in secs) to read data [default " + str(archive_freq) + " sec]", \
                    type=int)
parser.add_argument("-t", "--time", help="Time (in mins) to run [default " + str(run_time) + " min ]. -1 denotes run\
 forever.", type=int)
parser.add_argument("-v", "--verbosity", help="Verbosity level (0-2). [default = 2, most verbose].", type=int)

# Read arguments passed on command line
args = parser.parse_args()
fname = ''  # filename to log to

# Parse command line arguments
server_addr: str = args.serverIP  # Server IP  - not optional
if not (valid_ip(server_addr)):
    console_message("IP address " + server_addr + " invalid. Exiting.", ERRO)
    exit(-1)
if args.log:  # Log filename - optional
    fname = args.log
    logging = True
if args.freq != None:  # Read frequency - optional (default defined above)
    archive_freq = args.freq
    if archive_freq <= 0:
        console_message("Invalid collection frequency (--freq) (" + str(archive_freq) + "). Exiting.", ERRO)
        exit(-1)
if args.time != None:  # Run duration - optional (default defined above)
    run_time = args.time
    if run_time < 0:
        console_message("Invalid run duration (--time) (" + str(run_time) + "). Exiting.", ERRO)
        exit(-1)

if args.verbosity != None:  # Verbosity level - option (default defined above)
    verbosity = args.verbosity
    print("found v parm = " + str(verbosity))
    if verbosity <= 0:
        verbosity = 0
    elif verbosity >= 2:
        verbosity = 2
    print("requal v parm = " + str(verbosity))

if logging:
    # Open the file and write the header
    f = open(fname, 'a')
    f.write("Date Time,Press(mBar),Temp(c),Depth(m)\n")

# Write initial parameters to console
console_message("Logger started with following parms:", INFO)
if logging:
    console_message("     Saving to file     : " + fname)
console_message("     Server IP#         : " + server_addr)
console_message("     Logging frequency  : " + str(archive_freq) + " seconds")
if run_time <= 0:
    console_message("     Acquiring data until stopped via user interrupt (ctrl-c)")
else:
    console_message("     Acquiring data for : " + str(run_time) + " minutes")
curr_date_time = datetime.datetime.now()
console_message("\n     Acquisition started : " + str(curr_date_time.strftime("%Y%m%d")) + " at " + \
                str(curr_date_time.strftime("%H:%M:%S")) + "\n")

# Main loop
while True:
    try:
        if logging:
            f = open(fname, 'a')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)  # Set timeout for no response from server
        s.connect((server_addr, PORT))
        curr_date_time = datetime.datetime.now()
        data = s.recv(1024)
        # populate list with elements of pressure, temperature
        elem = data.split(b',')  # type : List[str]
        depth_meters = elem[2]
        depth_feet = float(depth_meters) * 3.28084
        curr_date = str(curr_date_time.strftime("%Y%m%d"))
        curr_time = str(curr_date_time.strftime("%H:%M:%S"))
        time_line = curr_date + ' ' + curr_time
        data_line = time_line + ',' + data.decode("utf-8")

        if logging:
            f.write(data_line + '\n')
        console_message("Server reports : " + data.decode("utf-8"), INFO)
        if run_time <= 0:
            console_message("Run time       : " + str(accum_time) + " seconds", INFO)
        else:
            console_message("Run time       : " + str(accum_time) + " of " + str(int(run_time) * 60) + " seconds", INFO)
        console_message("Current depth  : " + "{0:.2f}".format(float(depth_meters)) + " meters (" + "{0:.2f}".format(
            depth_feet) + " ft)", INFO)
        if logging:
            f.close()
            s.close()
        time.sleep(float(archive_freq))
        accum_time = accum_time + float(archive_freq)
        if (run_time > 0) & (accum_time > int(run_time) * 60):
            console_message("Acquisition complete.", INFO)
            f.close()
            s.close()
            exit(0)
    except socket.timeout:
        console_message("Timeout waiting for server response.", WARN)
    except KeyboardInterrupt:
        if logging:
            f.close()
            s.close()
        if run_time <= 0:
            console_message("Program terminated via user interrupt.", INFO)
            exit(0)
        else:
            console_message("Unexpected program termination via user interrupt.", WARN)
            exit(-1)
