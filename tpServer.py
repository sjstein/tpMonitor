#!/usr/bin/python3
# take the cr out
# Built-in packages:
from argparse import ArgumentParser
from datetime import date
import socket
import sys
import threading
import time

# Project-locals:
from tpUtilities import get_interface_devices
from tpUtilities import V_HIGH
from tpUtilities import TpLogger

log = TpLogger(V_HIGH)

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
    log.disp('\n    *** WARNING ***     ')
    log.disp('Operating in DEBUG mode!')
    log.disp(' USING MOCK SENSOR DATA \n')
    import mock_ms5837 as ms5837
else:
    import ms5837

# Retrieve all interface device infos:
interface_info = get_interface_devices()

# If the command line arg device is not found, error out:
HOST = interface_info.get(args.interface)
if HOST is None:
    log.erro(f'Device {args.interface} not found.')
    log.disp('\tAvailable interfaces:')
    for interface, address in interface_info.items():
        log.disp(f'\t\t{interface} : {address}')
    log.erro('Exiting')
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
            log.erro(msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : ' +
                      str(addr), fname)
            conn.close()
            return -1

        if str(data.decode('utf-8')).startswith(MSG_READ_ALL):
            log.info(msg_head + 'READ_ALL request from client : ' + str(addr), fname)
            try:
                if sensor.read():
                    pres = sensor.pressure()  # mbar (no arguments)
                    temp = sensor.temperature()  # degrees C (no arguments)
                    dept = sensor.depth()  # Saltwater depth (m)
                    data = str(round(pres,3)) + ',' + str(round(temp,3)) + ',' + str(round(dept,3))
                    log.info(msg_head + 'Server sent: ' + data, fname)
                    conn.send(data.encode())
                    timeout = 2  # Reset retry counter

                else:
                    log.warn(msg_head + 'I2C Sensor read failure, sending err(0),-1,-1 to client', fname)
                    data = '-1,-1,-1'
                    conn.send(data.encode())
                    log.warn(msg_head + 'Delaying ' + str(timeout) + ' seconds before retry', fname)
                    time.sleep(timeout)
                    timeout = timeout + 1

            except OSError as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                log.erro(msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : '
                          + str(addr), fname)
                conn.close()
                return -1

        elif str(data.decode('utf-8')).startswith(MSG_DISCONNECT):
            log.info(msg_head + 'DISCONNECT requested from client : ' + str(addr), fname)
            conn.close()
            log.info(msg_head + 'Client ' + str(addr) + ' : connection closed', fname)
            return 1

        else:
            try:
                log.warn(msg_head + 'Unknown command received from client : ' + str(addr) + ' [' + \
                          data.decode('utf-8') + ']', fname)
                response = 'CMD_UNKNOWN : ' + data.decode('utf-8')
                conn.send(response.encode())

            except OSError as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                log.erro(msg_head + 'Unexpected error (' + str(msg) + ') connection closed from client : ' +
                          str(addr), fname)
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
    log.info('|SUPR| Server started : ' + HOST + '(' + str(PORT) + ')', fname)

    retry = 2  # Timer for retries

    # initialize the sensor
    while True:
        try:
            if sensor.init():
                log.info('|SUPR| I2C Sensor initialized', fname)
                retry = 2  # Reset timer
                break
        except:
            log.info('|SUPR| Init sensor failed. Retrying after ' + str(retry) + ' Seconds', fname)
            time.sleep(retry)
            retry = retry + 1

    # We have to read initial values from sensor to update pressure and temperature
    if not sensor.read():
        log.erro('|SUPR| Initial sensor read failed - exiting', fname)
        exit(1)

    log.info('|SUPR| Initial Pressure: '
             + str(round(sensor.pressure(ms5837.UNITS_atm), 3)) + ' atm, '
             + str(round(sensor.pressure(ms5837.UNITS_Torr), 3)) + ' Torr, '
             + str(round(sensor.pressure(ms5837.UNITS_psi), 3)) + ' psi', fname)

    log.info('|SUPR| Initial Temperature: '
             + str(round(sensor.temperature(ms5837.UNITS_Centigrade), 3)) + ' C, '
             + str(round(sensor.temperature(ms5837.UNITS_Farenheit), 3)) + ' F, '
             + str(round(sensor.temperature(ms5837.UNITS_Kelvin), 3)) + ' K', fname)

    freshwaterDepth = sensor.depth()  # default is freshwater
    sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
    saltwaterDepth = sensor.depth()  # No need to read() again

    # NOTE: Leaving density set for saltwater as this is most common use case

    log.info('|SUPR| Initial Depth: '
             + str(round(freshwaterDepth, 3)) + ' m (freshwater), '
             + str(round(saltwaterDepth, 3)) + ' m (saltwater)', fname)

    log.info('|SUPR| Initial Altitude: '
             + str(round(sensor.altitude(), 3)) + ' m', fname)

    time.sleep(5)

    # Main loop
    while True:
        log.info('|SUPR| waiting for new client connection...', fname)
        connection, address = s.accept()     # Wait for connection request from client
        log.info('|SUPR| Connection accepted from : ' + str(address), fname)
        t = threading.Thread(target=threaded_client, args=(connection, address),name='T' + str(tid).zfill(3))
        t.start()
        tid = tid + 1
        if tid > MAXTID:
            tid = 0
        log.info('|SUPR| Current number of client threads : {0}'.format(str(threading.activeCount() - 1)), fname)
