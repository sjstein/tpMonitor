import argparse
import os
import socket
import sys
import time

from datetime import datetime

# Project-locals
from aspLibs.aspUtilities import valid_ip, IntRange, retry_connect
from aspLibs.aspUtilities import V_NONE, V_MED, V_HIGH
from aspLibs.aspUtilities import DATA_DIR
from aspLibs.aspUtilities import AspLogger


# Variable declaration section
archive_freq = 5    # Default archive frequency in seconds
run_time = 60       # Default run time in minutes
logging = False     # Default to no logging
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

MSG_READ_ALL = b'r all'
MSG_DISCONNECT = b'discon'

FILE_EXT = 'txt'

# Set up argument parser
# noinspection PyTypeChecker
parser = argparse.ArgumentParser(description='Python script to query a remote server for temperature and pressure\
 data, and optionally write that data to a text file.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('serverIP', help='IP Number of server.')
parser.add_argument('-f', '--freq', help='Frequency (in seconds) to read data.',
                    type=IntRange(1, ), default=archive_freq)
parser.add_argument('-l', '--log', help=f'File name for logging (extension \'.{FILE_EXT}\' is added).')

parser.add_argument('-t', '--time', help='Time (in minutes) to run (-1 denotes run forever, \
0 denotes run for one iteration).', type=IntRange(-1,), default=run_time)
parser.add_argument('-v', '--verbosity', help='Verbosity level 0 (silent) to 3 (most verbose).',
                    type=IntRange(V_NONE, V_HIGH), default=V_HIGH)

# Read arguments passed on command line
args = parser.parse_args()
fname = ''  # filename to log to
# create logging methods based on verbosity level
log = AspLogger(args.verbosity)

# Parse command line arguments
server_addr = args.serverIP  # Server IP  - not optional

if not (valid_ip(server_addr)):
    log.erro('IP address ' + server_addr + ' invalid. Exiting.')
    exit(-1)
if args.log is not None:  # Log filename - optional
    fname = args.log
    # Check for valid filename?
    logging = True
if args.freq is not None:  # Read frequency (seconds) - optional (default defined above)
    archive_freq = args.freq
if args.time is not None:  # Run duration (minutes) - optional (default defined above)
    run_time = args.time

if logging:
    now = datetime.now()
    datestr = now.strftime('%Y%m%d')
    # Check if data subdirectories exists, and if not create
    if not os.path.isdir(DATA_DIR):
        os.mkdir(DATA_DIR)
    data_path = f'{DATA_DIR}/{datestr}'
    if not os.path.isdir(data_path):
        os.mkdir(data_path)
    fqname = f'{data_path}/{fname}.{FILE_EXT}'
    idx = 1
    while os.path.isfile(fqname):
        fqname = f'{data_path}/{fname}_{idx}.{FILE_EXT}'
        idx += 1
    # Open the file and write the header
    f = open(fqname, 'a')
    f.write('Date Time,Press(mBar),Temp(c),Depth(m)\n')

# Write initial parameters to console
log.info('Acquisition started with following parameters:')
if logging:
    log.info('     Saving to file     : ' + fqname)
log.info('     Server IP#         : ' + server_addr)
log.info('     Logging frequency  : ' + str(archive_freq) + ' seconds')
if run_time == -1:
    log.info('     Acquiring data until stopped via user interrupt (ctrl-c)')
elif run_time == 0:
    log.info('     Acquiring data for one iteration')
else:
    log.info('     Acquiring data for : ' + str(run_time) + ' minutes')
log.info('')
# Set up socket for messages
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
retry_connect(logobj=log, sock=s, saddr=server_addr, sport=PORT)

# Main Loop
while True:
    try:
        s.sendall(MSG_READ_ALL)
        data = s.recv(1024)
        # populate list with elements of pressure, temperature
        elem = data.split(b',')  # type : List[str]
        temp_c = elem[1]
        temp_f = float(temp_c) * (9.0 / 5.0) + 32
        depth_meters = elem[2]
        depth_feet = float(depth_meters) * 3.28084

        if logging:
            data_line = f'{log.timestamp()},{data.decode("utf-8")}'
            f = open(fqname, 'a')
            f.write(data_line + '\n')
            f.close()
        if run_time < 0:
            log.info('Run time       : ' + str(accum_time) + ' seconds')
        else:
            log.info('Run time       : ' + str(accum_time) + ' of ' + str(int(run_time) * 60) + ' seconds')
        log.info('Current depth  : ' + '{0:.2f}'.format(float(depth_meters)) + ' meters (' + '{0:.2f}'.format(
            depth_feet) + ' ft)')
        log.info('Current temp   : ' + '{0:.2f}'.format(float(temp_c)) + ' deg C (' + '{0:.2f}'.format(
            temp_f) + ' deg F)')
        log.info('')

        if (run_time > 0) and (accum_time >= int(run_time) * 60) or run_time == 0:
            log.info('Acquisition complete.')
            s.sendall(MSG_DISCONNECT)
            s.close()
            exit(0)
        time.sleep(archive_freq)
        accum_time += archive_freq

    except ConnectionError as exc:
        log.warn(f'Problem connecting to server: {exc}')
        s.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retry_connect(logobj=log, sock=s, saddr=server_addr, sport=PORT)

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

