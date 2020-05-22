import argparse
import socket
import datetime
import time
import sys

# Project-locals
from utilities import valid_ip, IntRange
from utilities import ERRO, WARN, INFO, V_NONE, V_LOW, V_MED, V_HIGH
from utilities import Logger


# Variable declaration section
archive_freq = 5    # Default archive frequency in seconds
run_time = 60       # Default run time in minutes
logging = False     # Default to no logging
verbosity = V_HIGH  # Default to most verbose status messages
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
log = Logger()

prog_name = '{' + sys.argv[0] + '}'

# Constants
PORT = 5005  # TCP port for connection to server

MSG_READ_ALL = b'r all'
MSG_DISCONNECT = b'discon'


# Set up argument parser
parser = argparse.ArgumentParser(description='Python script to query a remote server for temperature and pressure\
 data, and optionally write that data to a text file.')
parser.add_argument('serverIP', help='IP Number of server.')
parser.add_argument('-l', '--log', help='File name for logging (default is NO logging).')
parser.add_argument('-f', '--freq', help='Frequency (in secs) to read data [default ' + str(archive_freq) + ' sec].',
                    type=IntRange(1,))
parser.add_argument('-t', '--time', help='Time (in mins) to run [default ' + str(run_time) + ' min ]. -1 denotes run\
 forever, 0 denotes run for one iteration.', type=IntRange(-1,))
parser.add_argument('-v', '--verbosity', help='Verbosity level (0-3) [0 = suppress all; 3 (default) = most verbose].',
                    type=IntRange(V_NONE, V_HIGH))

# Read arguments passed on command line
args = parser.parse_args()
fname = ''  # filename to log to

# Parse command line arguments
server_addr = args.serverIP  # Server IP  - not optional

if not (valid_ip(server_addr)):
    log.erro('IP address ' + server_addr + ' invalid. Exiting.')
    exit(-1)
if args.log is not None:  # Log filename - optional
    fname = args.log
    logging = True
if args.freq is not None:  # Read frequency (seconds) - optional (default defined above)
    archive_freq = args.freq
if args.time is not None:  # Run duration (minutes) - optional (default defined above)
    run_time = args.time
if args.verbosity is not None:  # Verbosity level - option (default defined above)
    verbosity = args.verbosity
log.verbosity = verbosity

if logging:
    # Open the file and write the header
    f = open(fname, 'a')
    f.write('Date Time,Press(mBar),Temp(c),Depth(m)\n')

# Write initial parameters to console
log.info('Logger started with following parameters:')
if logging:
    log.info('     Saving to file     : ' + fname)
log.info('     Server IP#         : ' + server_addr)
log.info('     Logging frequency  : ' + str(archive_freq) + ' seconds')
if run_time == -1:
    log.info('     Acquiring data until stopped via user interrupt (ctrl-c)')
elif run_time == 0:
    log.info('     Acquiring data for one iteration')
else:
    log.info('     Acquiring data for : ' + str(run_time) + ' minutes')
curr_date_time = datetime.datetime.now()
log.info('     Acquisition started : ' + str(curr_date_time.strftime('%Y%m%d')) + ' at ' + \
                str(curr_date_time.strftime('%H:%M:%S')))
log.info('')
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
        curr_date = str(curr_date_time.strftime('%Y%m%d'))
        curr_time = str(curr_date_time.strftime('%H:%M:%S'))
        time_line = curr_date + ' ' + curr_time
        data_line = time_line + ',' + data.decode('utf-8')

        if logging:
            f.write(data_line + '\n')
        if run_time < 0:
            log.info('Run time       : ' + str(accum_time) + ' seconds')
        else:
            log.info('Run time       : ' + str(accum_time) + ' of ' + str(int(run_time) * 60) + ' seconds')
        log.info('Current depth  : ' + '{0:.2f}'.format(float(depth_meters)) + ' meters (' + '{0:.2f}'.format(
            depth_feet) + ' ft)')
        log.info('Current temp   : ' + '{0:.2f}'.format(float(temp_c)) + ' deg C (' + '{0:.2f}'.format(
            temp_f) + ' deg F)')
        if verbosity > V_MED:
            log.info('')  # Blank line
        if logging:
            f.close()
        if (run_time > 0) and (accum_time >= int(run_time) * 60) or run_time == 0:
            log.info('Acquisition complete.')
            s.sendall(MSG_DISCONNECT)
            s.close()
            exit(0)
        time.sleep(float(archive_freq))
        accum_time = accum_time + float(archive_freq)

    except socket.timeout:
        log.warn('Timeout waiting for server response.')

    except IndexError:
        log.warn('Malformed message from server : ' + data.decode('utf-8'))

    except KeyboardInterrupt:
        if logging:
            f.close()
        if run_time <= 0:
            log.info('Program terminated via user interrupt.')
            exit(0)
        else:
            log.warn('Unexpected program termination via user interrupt.')
            exit(-1)

