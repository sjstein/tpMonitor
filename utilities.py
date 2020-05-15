from datetime import datetime
import fcntl
import socket
import struct
import subprocess



timestamp_format = '%Y%m%d %H:%M:%S'


def timestamp():
    return datetime.now().strftime(timestamp_format)


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
