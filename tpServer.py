#!/usr/bin/python3

# Built-in packages:
from argparse import ArgumentParser
from datetime import date
from datetime import datetime
import fcntl  # *nix only library - used to identify host ip#
import socket
import struct
import sys
import time

# Project-locals:
from utilities import get_interface_devices, timestamp


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

MSG_READ_ALL = 'r all'
MSG_DISCONNECT = 'discon'


# Begin function definition 'echo_stat(fdesc, msg)
def echo_stat(fdesc, loc_msg):
    print(("[" + str(datetime.now()) + "] " + loc_msg))
    fdesc.write("[" + str(datetime.now()) + "] " + loc_msg + "\n")
# End function definition


# Retrieve all interface device infos:
interface_info = get_interface_devices()

# If the command line arg device is not found, error out:
HOST = interface_info.get(args.interface)
if HOST is None:
    print(f'{timestamp()} [ERRO] Device {args.interface} not found.')
    print(f'{timestamp()} [ERRO] Available interfaces:')
    for interface, address in interface_info.items():
        print(f'{timestamp()} [ERRO]\t{interface} : {address}')
    print(f'{timestamp()} [ERRO] kthxbyee')
    sys.exit(-1)

PORT = 5005  # Server port

# Open port to accept remote requests
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Type : str
s.bind((HOST, PORT))
s.listen(1)

# Instantiate sensor using default I2C parameters
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)

fname = str(date.today()) + "_tpServer.log"
f = open(fname, 'a')  # Open log file (append)

echo_stat(f, "Server started")
echo_stat(f, "Server IP# : " + HOST)
echo_stat(f, "Server Port: " + str(PORT))

retry = 2  # Timer for retries

# initialize the sensor
while True:
    try:
        if sensor.init():
            echo_stat(f, "I2C Sensor initialized")
            retry = 2  # Reset timer
            break
    except:
        echo_stat(f, "Init sensor failed. Retrying after " + str(retry) + " Seconds")
        time.sleep(retry)
        retry = retry + 1

# We have to read initial values from sensor to update pressure and temperature
if not sensor.read():
    echo_stat(f, "Initial sensor read failed - exiting")
    exit(1)

echo_stat(f, "Initial Pressure: "
         + str(sensor.pressure(ms5837.UNITS_atm)) + " atm, "
         + str(sensor.pressure(ms5837.UNITS_Torr)) + " Torr, "
         + str(sensor.pressure(ms5837.UNITS_psi)) + " psi")

echo_stat(f, "Initial Temperature: "
         + str(sensor.temperature(ms5837.UNITS_Centigrade)) + " C, "
         + str(sensor.temperature(ms5837.UNITS_Farenheit)) + " F, "
         + str(sensor.temperature(ms5837.UNITS_Kelvin)) + " K")

freshwaterDepth = sensor.depth()  # default is freshwater
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
saltwaterDepth = sensor.depth()  # No need to read() again

# NOTE: Leaving density set for saltwater as this is most common use case

echo_stat(f, "Initial Depth: "
         + str(freshwaterDepth) + " m (freshwater), "
         + str(saltwaterDepth) + " m (saltwater)")

echo_stat(f, "Initial Altitude: "
         + str(sensor.altitude()) + " m")

time.sleep(5)

echo_stat(f, "Awaiting client connection")
conn, addr = s.accept()
echo_stat(f, "Client connected from IP: " + str(addr))

# Main loop

while True:
    data = conn.recv(160)
    if str(data.decode('utf-8')).startswith(MSG_READ_ALL):
        echo_stat(f, "Read ALL requested from client : " + str(addr))
        try:
            if sensor.read():
                pres = sensor.pressure()  # mbar (no arguments)
                temp = sensor.temperature()  # degrees C (no arguments)
                dept = sensor.depth()  # Saltwater depth (m)
                data = str(pres) + ',' + str(temp) + ',' + str(dept)
                echo_stat(f, "Server sent: " + data)
                conn.send(data.encode())
                retry = 2  # Reset retry counter

            else:
                echo_stat(f, "I2C Sensor read failure, sending err(0),-1,-1 to client")
                data = "-1,-1,-1"
                conn.send(data.encode())
                echo_stat(f, "Delaying " + str(retry) + " seconds before retry")
                time.sleep(retry)
                retry = retry + 1

        except socket.error as msg:
            # This exception will cover various socket errors such as a broken pipe (client disconnect)
            echo_stat(f, "Client (" + str(addr) + "): connection closed")
            conn.close()
            break

    elif str(data.decode('utf-8')).startswith(MSG_DISCONNECT):
        echo_stat(f, "DISCONNECT requested from client : " + str(addr))
        conn.close()
        echo_stat(f, "Client (" + str(addr) + "): connection closed")
        echo_stat(f, "Awaiting client connection")
        conn, addr = s.accept()
        echo_stat(f, "Client connected from IP: " + str(addr))

    else:
        try:
            echo_stat(f, "Unknown command sent from client : " + str(addr) + ' ' + data.decode('utf-8'))
            response = 'CMD_UNKNOWN : ' + data.decode('utf-8')
            echo_stat(f, "Server sent: " + response)
            conn.send(response.encode())

        except socket.error as msg:
            # This exception will cover various socket errors such as a broken pipe (client disconnect)
            echo_stat(f, "Client (" + str(addr) + "): connection closed")
            conn.close()
            break

