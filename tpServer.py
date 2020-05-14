#!/usr/bin/python3

import ms5837
import socket
import datetime
import fcntl  # *nix only library - used to identify host ip#
import struct
import time
import threading


# Function to return the IP number bound to a specific ethernet interface (ifname)
def get_ip_address(ifname):  # Type: any
    error_count = 0
    while True:
        try:
            loc_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(loc_s.fileno(), 0x8915, struct.pack(b'256s', ifname[:15]))[20:24])

        except:
            time.sleep(1)
            error_count += 1
            if error_count > 60:
                raise Exception('Unable to obtain ip# during tpServer start')


# Function to return a timestamp string
def timestamp():
    loc_date_time = datetime.datetime.now()
    loc_curr_date = str(loc_date_time.strftime('%Y%m%d'))
    loc_curr_time = str(loc_date_time.strftime('%H:%M:%S'))
    loc_time_line = loc_curr_date + ' ' + loc_curr_time
    return loc_time_line


# Function to write status messages to file and stdout
def echo_stat(fdesc, loc_msg):
    print(timestamp() + ' ' + loc_msg)
    fdesc.write(timestamp() + ' ' + loc_msg + '\n')


# Client handler - meant to be threaded
def threaded_client(conn, addr):
    timeout = 2     # Counter for back-off / retry
    tname = threading.current_thread().name
    msg_head = '[' + str(tname) + '] '    # Create message header with thread ID
    while True:
        data = conn.recv(160)
        if str(data.decode('utf-8')).startswith(MSG_READ_ALL):
            echo_stat(f, msg_head + 'Read ALL requested from client : ' + str(addr))
            try:
                if sensor.read():
                    pres = sensor.pressure()  # mbar (no arguments)
                    temp = sensor.temperature()  # degrees C (no arguments)
                    dept = sensor.depth()  # Saltwater depth (m)
                    data = str(round(pres,3)) + ',' + str(round(temp,3)) + ',' + str(round(dept,3))
                    echo_stat(f, msg_head + 'Server sent: ' + data)
                    conn.send(data.encode())
                    timeout = 2  # Reset retry counter

                else:
                    echo_stat(f, msg_head + 'I2C Sensor read failure, sending err(0),-1,-1 to client')
                    data = '-1,-1,-1'
                    conn.send(data.encode())
                    echo_stat(f, msg_head + 'Delaying ' + str(timeout) + ' seconds before retry')
                    time.sleep(timeout)
                    timeout = timeout + 1

            except socket.error as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                echo_stat(f, msg_head + 'Unexpected error, connection closed from client : ' + str(addr))
                conn.close()
                return -1

        elif str(data.decode('utf-8')).startswith(MSG_DISCONNECT):
            echo_stat(f, msg_head + 'DISCONNECT requested from client : ' + str(addr))
            conn.close()
            echo_stat(f, msg_head + 'Client ' + str(addr) + ' : connection closed')
            return 1

        else:
            try:
                echo_stat(f, msg_head + 'Unknown command received from client : ' + str(addr) + ' [' + \
                          data.decode('utf-8') + ']')
                response = 'CMD_UNKNOWN : ' + data.decode('utf-8')
                conn.send(response.encode())

            except socket.error as msg:
                # This exception will cover various socket errors such as a broken pipe (client disconnect)
                echo_stat(f, msg_head + 'Unexpected error, connection closed from client : ' + str(addr))
                conn.close()
                return -1


# Main program begins

MSG_READ_ALL = 'r all'
MSG_DISCONNECT = 'discon'
HOST = get_ip_address(b'eth0')  # Determine IP# on eth0
PORT = 5005     # Server port
MAXTID = 9999   # Maximum TID
tid = 0         # Thread ID number

# Open port to accept remote requests
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Type : str
s.bind((HOST, PORT))
s.listen(1)

# Instantiate sensor using default I2C parameters
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)

# Open logging file (append mode)
fname = str(datetime.date.today()) + '_tpServer.log'
f = open(fname, 'a')  # Open log file (append)

echo_stat(f, '[SUP] Server started : ' + HOST + '(' + str(PORT) + ')')

retry = 2  # Timer for retries

# initialize the sensor
while True:
    try:
        if sensor.init():
            echo_stat(f, '[SUP] I2C Sensor initialized')
            retry = 2  # Reset timer
            break
    except:
        echo_stat(f, '[SUP] Init sensor failed. Retrying after ' + str(retry) + ' Seconds')
        time.sleep(retry)
        retry = retry + 1

# We have to read initial values from sensor to update pressure and temperature
if not sensor.read():
    echo_stat(f, '[SUP] Initial sensor read failed - exiting')
    exit(1)

echo_stat(f, '[SUP] Initial Pressure: '
         + str(round(sensor.pressure(ms5837.UNITS_atm), 3)) + ' atm, '
         + str(round(sensor.pressure(ms5837.UNITS_Torr), 3)) + ' Torr, '
         + str(round(sensor.pressure(ms5837.UNITS_psi), 3)) + ' psi')

echo_stat(f, '[SUP] Initial Temperature: '
         + str(round(sensor.temperature(ms5837.UNITS_Centigrade), 3)) + ' C, '
         + str(round(sensor.temperature(ms5837.UNITS_Farenheit), 3)) + ' F, '
         + str(round(sensor.temperature(ms5837.UNITS_Kelvin), 3)) + ' K')

freshwaterDepth = sensor.depth()  # default is freshwater
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
saltwaterDepth = sensor.depth()  # No need to read() again

# NOTE: Leaving density set for saltwater as this is most common use case

echo_stat(f, '[SUP] Initial Depth: '
         + str(round(freshwaterDepth, 3)) + ' m (freshwater), '
         + str(round(saltwaterDepth, 3)) + ' m (saltwater)')

echo_stat(f, '[SUP] Initial Altitude: '
         + str(round(sensor.altitude(), 3)) + ' m')

time.sleep(5)

# Main loop
while True:
    echo_stat(f, '[SUP] waiting for client connection...')
    connection, address = s.accept()     # Wait for connection request from client
    echo_stat(f, '[SUP] Connection accepted from : ' + str(address))
    t = threading.Thread(target=threaded_client, args=(connection, address),name='TID#' + str(tid))
    t.start()
    tid = tid + 1
    if tid > MAXTID:
        tid = 0
    echo_stat(f, '[SUP] Current number of client threads : {0}'.format(str(threading.activeCount() - 1)))
