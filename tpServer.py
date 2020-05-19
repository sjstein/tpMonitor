#!/usr/bin/python3

# Built-in packages:
from argparse import ArgumentParser
from datetime import date
from datetime import datetime
import socket
import sys
import threading
import time

# Project-locals:
from utilities import get_interface_devices, console_message, echo_stat
from utilities import INFO, WARN, ERRO

parser = ArgumentParser()
parser.add_argument('--debug',
                    action='store_true',
                    help='When set, use synthetic data')
parser.add_argument('-i',
                    '--interface',
                    default='eth0',
                    dest='interface',
                    help='Interface device name to use')
args = parser.parse_args()

# Conditionally import mock or hardware sensor module:
if args.debug:
    print('    *** WARNING ***     ')
    print('Operating in DEBUG mode!')
    print(' USING MOCK SENSOR DATA ')
    import mock_ms5837 as ms5837
else:
    import ms5837

# Retrieve all interface device infos:
interface_info = get_interface_devices()

# If the command line arg device is not found, error out:
HOST = interface_info.get(args.interface)
if HOST is None:
    console_message(f'Device {args.interface} not found.', ERRO)
    console_message('\tAvailable interfaces:', None)
    for interface, address in interface_info.items():
        console_message(f'\t\t{interface} : {address}', None)
    console_message('Exiting', ERRO)
    sys.exit(-1)


# Client handler - meant to be threaded
def threaded_client(conn, addr):
    timeout = 2     # Counter for back-off / retry
    tname = threading.current_thread().name
    msg_head = '|' + str(tname) + '| '    # Create message header with thread ID
    while True:
        try:
            data = conn.recv(160)

        except OSError as msg:
            # This exception will cover various socket errors such as a broken pipe (client disconnect)
            echo_stat(fname, msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : ' +
                      str(addr), ERRO)
            conn.close()
            return -1

        if str(data.decode('utf-8')).startswith(MSG_READ_ALL):
            echo_stat(fname, msg_head + 'READ_ALL request from client : ' + str(addr), INFO)
            try:
                if sensor.read():
                    pres = sensor.pressure()  # mbar (no arguments)
                    temp = sensor.temperature()  # degrees C (no arguments)
                    dept = sensor.depth()  # Saltwater depth (m)
                    data = str(round(pres,3)) + ',' + str(round(temp,3)) + ',' + str(round(dept,3))
                    echo_stat(fname, msg_head + 'Server sent: ' + data, INFO)
                    conn.send(data.encode())
                    timeout = 2  # Reset retry counter

                else:
                    echo_stat(fname, msg_head + 'I2C Sensor read failure, sending err(0),-1,-1 to client', WARN)
                    data = '-1,-1,-1'
                    conn.send(data.encode())
                    echo_stat(fname, msg_head + 'Delaying ' + str(timeout) + ' seconds before retry', WARN)
                    time.sleep(timeout)
                    timeout = timeout + 1

            except OSError as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                echo_stat(fname, msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : '
                          + str(addr), ERRO)
                conn.close()
                return -1

        elif str(data.decode('utf-8')).startswith(MSG_DISCONNECT):
            echo_stat(fname, msg_head + 'DISCONNECT requested from client : ' + str(addr), INFO)
            conn.close()
            echo_stat(fname, msg_head + 'Client ' + str(addr) + ' : connection closed', INFO)
            return 1

        else:
            try:
                echo_stat(fname, msg_head + 'Unknown command received from client : ' + str(addr) + ' [' + \
                          data.decode('utf-8') + ']', WARN)
                response = 'CMD_UNKNOWN : ' + data.decode('utf-8')
                conn.send(response.encode())

            except OSError as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                echo_stat(fname, msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : ' +
                          str(addr), ERRO)
                conn.close()
                return -1


# Main program begins

MSG_READ_ALL = 'r all'
MSG_DISCONNECT = 'discon'
PORT = 5005     # Server port
MAXTID = 999   # Maximum TID
tid = 0         # Thread ID number

# Open port to accept remote requests
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)

    # Instantiate sensor using default I2C parameters
    sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)

    # Open logging file (append mode) and write header
    fname = str(date.today()) + '_tpServer.log'
    echo_stat(fname, '|SUPR| Server started : ' + HOST + '(' + str(PORT) + ')', INFO)

    retry = 2  # Timer for retries

    # initialize the sensor
    while True:
        try:
            if sensor.init():
                echo_stat(fname, '|SUPR| I2C Sensor initialized', INFO)
                retry = 2  # Reset timer
                break
        except:
            echo_stat(fname, '|SUPR| Init sensor failed. Retrying after ' + str(retry) + ' Seconds', INFO)
            time.sleep(retry)
            retry = retry + 1

    # We have to read initial values from sensor to update pressure and temperature
    if not sensor.read():
        echo_stat(fname, '|SUPR| Initial sensor read failed - exiting', INFO)
        exit(1)

    echo_stat(fname, '|SUPR| Initial Pressure: '
             + str(round(sensor.pressure(ms5837.UNITS_atm), 3)) + ' atm, '
             + str(round(sensor.pressure(ms5837.UNITS_Torr), 3)) + ' Torr, '
             + str(round(sensor.pressure(ms5837.UNITS_psi), 3)) + ' psi', INFO)

    echo_stat(fname, '|SUPR| Initial Temperature: '
             + str(round(sensor.temperature(ms5837.UNITS_Centigrade), 3)) + ' C, '
             + str(round(sensor.temperature(ms5837.UNITS_Farenheit), 3)) + ' F, '
             + str(round(sensor.temperature(ms5837.UNITS_Kelvin), 3)) + ' K', INFO)

    freshwaterDepth = sensor.depth()  # default is freshwater
    sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
    saltwaterDepth = sensor.depth()  # No need to read() again

    # NOTE: Leaving density set for saltwater as this is most common use case

    echo_stat(fname, '|SUPR| Initial Depth: '
             + str(round(freshwaterDepth, 3)) + ' m (freshwater), '
             + str(round(saltwaterDepth, 3)) + ' m (saltwater)', INFO)

    echo_stat(fname, '|SUPR| Initial Altitude: '
             + str(round(sensor.altitude(), 3)) + ' m', INFO)

    time.sleep(5)

    # Main loop
    while True:
        echo_stat(fname, '|SUPR| waiting for client connection...', INFO)
        connection, address = s.accept()     # Wait for connection request from client
        echo_stat(fname, '|SUPR| Connection accepted from : ' + str(address), INFO)
        t = threading.Thread(target=threaded_client, args=(connection, address),name='T' + str(tid).zfill(3))
        t.start()
        tid = tid + 1
        if tid > MAXTID:
            tid = 0
        echo_stat(fname, '|SUPR| Current number of client threads : {0}'.format(str(threading.activeCount() - 1)), INFO)
