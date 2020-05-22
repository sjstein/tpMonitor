from datetime import datetime
import re
import subprocess
import sys
import argparse


time_shortform = '%Y%m%d %H:%M:%S'
time_longform = '%Y%m%d %H:%M:%S.%f'
# so take the cr out
ERRO = 0  # Message types for console_message function
WARN = 1
INFO = 2
DISP = 3

V_NONE = 0
V_LOW = 1
V_MED = 2
V_HIGH = 3

class IntRange:
    """
    Class used to validate that a CL argument (int type) is within
    [min,max] range. Utilized with 'type' parameter of add_argument.
    e.g.
    argparse.add_argument('...',type=IntRange,...)
    """

    def __init__(self, imin=None, imax=None):
        self.imin = imin
        self.imax = imax

    def __call__(self, arg):
        try:
            value = int(arg)
        except ValueError:
            raise self.exception()
        if (self.imin is not None and value < self.imin) or (self.imax is not None and value > self.imax):
            raise self.exception()
        return value

    def exception(self):
        if self.imin is not None and self.imax is not None:
            return argparse.ArgumentTypeError(f'Must be an integer in the range [{self.imin}, {self.imax}]')
        elif self.imin is not None:
            return argparse.ArgumentTypeError(f'Must be an integer >= {self.imin}')
        elif self.imax is not None:
            return argparse.ArgumentTypeError(f'Must be an integer <= {self.imax}')
        else:
            return argparse.ArgumentTypeError('Must be an integer')


class Logger:

    verbosity = 0

    def __init__(self, msg='', dest=None):
        self.msg = msg
        self.dest = dest

    def info(self, msg='', dest=None):
        console_message(msg, INFO, self.verbosity)
        return

    def warn(self, msg='', dest=None):
        console_message(msg, WARN, self.verbosity)
        return

    def erro(self, msg='', dest=None):
        console_message(msg, ERRO, self.verbosity)
        return

    def disp(self, msg='', dest=None):
        console_message(msg, DISP, self.verbosity)
        return


def timestamp():
    return datetime.now().strftime(time_shortform)

# Function to validate IPv4 address
def valid_ip(ip_nbr):
    # Create regular expression used to evaluate ipv4 address
    regex_ip = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.( 
                25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''

    if re.search(regex_ip, ip_nbr):
        return True  # IP address is properly formed
    else:
        return False  # IP address is malformed


# Function to print message on console
def console_message(msg='', severity=None, verbosity=V_HIGH):
    if not msg:  # To send a blank line to console, call function with no msg
        print('')
        return ()
    prog_name = '{' + sys.argv[0] + '}'
    if severity == ERRO and verbosity > V_NONE:
        print(timestamp() + ' [ERRO] ' + msg + ' ' + prog_name)
    elif severity == WARN and verbosity > V_LOW:
        print(timestamp() + ' [WARN] ' + msg + ' ' + prog_name)
    elif severity == INFO and verbosity > V_MED:
        print(timestamp(), ' [INFO] ', msg, prog_name)
    elif severity == DISP and verbosity > V_NONE:
        print(msg)


# Function to write status to both console and log file
def echo_stat(fname, loc_msg, severity=3):
    console_message(loc_msg, severity,)
    with open(fname, 'a') as f:
        f.write('[' + str(datetime.now()) + '] ' + loc_msg + '\n')


def get_interface_devices():
    """
    For operating systems that respond in a predictable way to the 
    command
        
        ip -4 addr show

    this utility will parse the result and produce a dictionary keyed by
    interface device name strings, and valued with their IP addresses as
    strings.  

    If the OS does not support the subprocess call, presumably the call
    will raise *some* kind of exception, which we report and then return
    an empty dictionary.  

    The expected format for results from the "ip" command is:

        id: name: ...
            inet addr/ ...

    This method identifies each hardware device by finding output lines
    that start with an integer device id.  From there it extracts the 
    device name and addr.  
    """

    # Execute the command:
    ip_command = ['ip', '-4', 'addr', 'show']
    try:
        output_bytes = subprocess.check_output(ip_command)
    except Exception as e:
        print(e)
        return dict()

    # Convert the output:
    output_string = output_bytes.decode()
    output_lines = output_string.split('\n')

    # Parse the output for lines containing device IDs:
    device_line_indices = list()
    for idx, line in enumerate(output_lines):
        try:
            # If the first segment of the ':'-split line will cast to 
            # int it's an id, and this line defines an interface device:
            int(line.split(':')[0])
            device_line_indices.append(idx)
        except ValueError:
            pass

    # Parse the output to extract device name/addr:
    interface_devices = dict()
    for idx in device_line_indices:
        # The name is the second segment of the ':'-split line:
        device = output_lines[idx].split(':')[1].strip()
        # The following line has the address after 'inet'; in other 
        # words, the second segment after stripping leading whitespace
        # and splitting on ' ':
        address = output_lines[idx+1].strip().replace('/', ' ').split()[1]
        interface_devices.update({device: address})

    return interface_devices
