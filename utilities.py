from datetime import datetime
import re
import subprocess
import sys


timestamp_format = '%Y%m%d %H:%M:%S'

ERRO = 2  # Message types for console_message function
WARN = 1
INFO = 0


def timestamp():
    return datetime.now().strftime(timestamp_format)

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
def console_message(msg='', severity=3, verbosity=2):
    if not msg:  # To send a blank line to console, call function with no msg
        print('')
        return ()
    prog_name = '{' + sys.argv[0] + '}'
    if severity == ERRO:
        print((timestamp() + " [ERRO] " + msg + " " + prog_name))
    elif severity == WARN and verbosity > 0:
        print((timestamp() + " [WARN] " + msg + " " + prog_name))
    elif severity == INFO and verbosity > 1:
        print((timestamp() + " [INFO] " + msg + " " + prog_name))
    elif verbosity > 1:
        print(msg)
    return ()


# Function to write status to both console and log file
def echo_stat(fname, loc_msg, severity=3):
    console_message(loc_msg, severity,)
    with open(fname, 'a') as f:
        f.write("[" + str(datetime.now()) + "] " + loc_msg + "\n")


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
