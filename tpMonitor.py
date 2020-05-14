import argparse
import socket
import datetime
import time
import re
import sys

# Variable declaration section
archive_freq = 5    # Default archive frequency in seconds
run_time = 60       # Default run time in minutes
logging = False     # Default to no logging
verbosity = 2       # Default to most verbose status messages
accum_time = 0      # Counter to hold total run time
depth_meters = 0.0
depth_feet = 0.0
temp_c = 0.0
temp_f = 0.0
f = ''  # file object
s = ''  # socket object
data = ''  # Return string from server
curr_time = ''
curr_date = ''

prog_name = '{' + sys.argv[0] + '}'

# Constants
PORT = 5005  # TCP port for connection to server
ERRO = 2  # Message types
WARN = 1
INFO = 0
MSG_READ_ALL = b'r all'
MSG_DISCONNECT = b'discon'


# Function to validate IPv4 address
def valid_ip(ip_nbr):
    # Create regular expression used to evaluate ipv4 address
    regex_ip = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

    if re.search(regex_ip, ip_nbr):
        return 1  # IP address is properly formed
    else:
        return 0  # IP address is malformed


# Function to return a timestamp string
def timestamp():
    loc_date_time = datetime.datetime.now()
    loc_curr_date = str(loc_date_time.strftime("%Y%m%d"))
    loc_curr_time = str(loc_date_time.strftime("%H:%M:%S"))
    loc_time_line = loc_curr_date + ' ' + loc_curr_time
    return loc_time_line


# Function to print message on console
def console_message(msg='', severity=3):
    if not msg:  # To send a blank line to console, call function with no msg
        print('')
        return ()
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
parser.add_argument("serverIP", help="IP Number of server.")
parser.add_argument("-l", "--log", help="File name for logging (default is NO logging).")
parser.add_argument("-f", "--freq", help="Frequency (in secs) to read data [default " + str(archive_freq) + " sec].",
                    type=int)
parser.add_argument("-t", "--time", help="Time (in mins) to run [default " + str(run_time) + " min ]. -1 denotes run\
 forever, 0 denotes run for one iteration.", type=int)
parser.add_argument("-v", "--verbosity", help="Verbosity level (0-2) [default = 2, most verbose].", type=int)

# Read arguments passed on command line
args = parser.parse_args()
fname = ''  # filename to log to

# Parse command line arguments
server_addr = args.serverIP  # Server IP  - not optional

if not (valid_ip(server_addr)):
    console_message("IP address " + server_addr + " invalid. Exiting.", ERRO)
    exit(-1)
if args.log is not None:  # Log filename - optional
    fname = args.log
    logging = True
if args.freq is not None:  # Read frequency (seconds) - optional (default defined above)
    archive_freq = args.freq
    if archive_freq <= 0:
        console_message("Invalid collection frequency (--freq) (" + str(archive_freq) + "). Exiting.", ERRO)
        exit(-1)
if args.time is not None:  # Run duration (minutes) - optional (default defined above)
    run_time = args.time
    if run_time < -1:   # Run time of (-1) denotes "run forever"
        console_message("Invalid run duration (--time) (" + str(run_time) + "). Exiting.", ERRO)
        exit(-1)
if args.verbosity is not None:  # Verbosity level - option (default defined above)
    verbosity = args.verbosity
    if verbosity <= 0:
        verbosity = 0
    elif verbosity >= 2:
        verbosity = 2

if logging:
    # Open the file and write the header
    f = open(fname, 'a')
    f.write("Date Time,Press(mBar),Temp(c),Depth(m)\n")

# Write initial parameters to console
console_message("Logger started with following parameters:", INFO)
if logging:
    console_message("     Saving to file     : " + fname)
console_message("     Server IP#         : " + server_addr)
console_message("     Logging frequency  : " + str(archive_freq) + " seconds")
if run_time == -1:
    console_message("     Acquiring data until stopped via user interrupt (ctrl-c)")
elif run_time == 0:
    console_message("     Acquiring data for one iteration")
else:
    console_message("     Acquiring data for : " + str(run_time) + " minutes")
curr_date_time = datetime.datetime.now()
console_message("\n     Acquisition started : " + str(curr_date_time.strftime("%Y%m%d")) + " at " + \
                str(curr_date_time.strftime("%H:%M:%S")) + "\n")

# Set up socket for messages
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)  # Set timeout for no response from server
s.connect((server_addr, PORT))

# Main Loop
while True:
    try:
        if logging:
            f = open(fname, 'a')
        s.sendall(MSG_READ_ALL)
        curr_date_time = datetime.datetime.now()
        data = s.recv(1024)
        # populate list with elements of pressure, temperature
        elem = data.split(b',')  # type : List[str]
        temp_c = elem[1]
        temp_f = float(temp_c) * (9.0 / 5.0) + 32
        depth_meters = elem[2]
        depth_feet = float(depth_meters) * 3.28084
        curr_date = str(curr_date_time.strftime("%Y%m%d"))
        curr_time = str(curr_date_time.strftime("%H:%M:%S"))
        time_line = curr_date + ' ' + curr_time
        data_line = time_line + ',' + data.decode("utf-8")

        if logging:
            f.write(data_line + '\n')
#       console_message("Server reports : " + data.decode("utf-8"), INFO)
        if run_time < 0:
            console_message("Run time       : " + str(accum_time) + " seconds", INFO)
        else:
            console_message("Run time       : " + str(accum_time) + " of " + str(int(run_time) * 60) + " seconds", INFO)
        console_message("Current depth  : " + "{0:.2f}".format(float(depth_meters)) + " meters (" + "{0:.2f}".format(
            depth_feet) + " ft)", INFO)
        console_message("Current temp   : " + "{0:.2f}".format(float(temp_c)) + " deg C (" + "{0:.2f}".format(
            temp_f) + " deg F)", INFO)
        console_message('')  # Blank line
        if logging:
            f.close()
            s.close()
        if (run_time > 0) and (accum_time >= int(run_time) * 60) or run_time == 0:
            console_message("Acquisition complete.", INFO)
            s.sendall(MSG_DISCONNECT)
            s.close()
            exit(0)
        time.sleep(float(archive_freq))
        accum_time = accum_time + float(archive_freq)

    except socket.timeout:
        console_message("Timeout waiting for server response.", WARN)

    except IndexError:
        console_message("Malformed message from server : " + data.decode("utf-8"), WARN)

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

