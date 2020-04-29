#!/usr/bin/python3

import ms5837
import socket
import fcntl  # *nix only library - used to identify host ip#
import struct
import time

from datetime import date
from datetime import datetime


# Begin function definition 'get_ip_address(ifname)'
#   A function to return the IP number bound to a specific ethernet interface (ifname)
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
                raise Exception("Unable to obtain ip# during tpServer start")
# End function definition


# Begin function definition 'statusOutput(fdesc, msg)
def echo_stat(fdesc, loc_msg):
    print(("[" + str(datetime.now()) + "] " + loc_msg))
    fdesc.write("[" + str(datetime.now()) + "] " + loc_msg + "\n")
# End function definition


HOST = get_ip_address(b'eth0')  # Determine IP# on eth0
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
saltwaterDepth = sensor.depth()  # No nead to read() again

# NOTE: Leaving density set for saltwater as this is most common use case

echo_stat(f, "Initial Depth: "
         + str(freshwaterDepth) + " m (freshwater), "
         + str(saltwaterDepth) + " m (saltwater)")

echo_stat(f, "Initial Altitude: "
         + str(sensor.altitude()) + " m")

time.sleep(5)

# Main loop
while True:
    conn, addr = s.accept()
    echo_stat(f, "Client connected from IP: " + str(addr))
    while True:
        data = conn.recv(256)
        print(str(data,"utf-8"))
        print(data[1:2])
        if not data:
            break
        if data[0:1] == b'r':  # read request
            try:
                if sensor.read():
                    pres = sensor.pressure()  # mbar (no arguments)
                    temp = sensor.temperature()  # degrees C (no arguments)
                    dept = sensor.depth()  # Saltwater depth (m)
                    data = str(pres) + ',' + str(temp) + ',' + str(dept)
                    echo_stat(f, "Server sent: " + data)
                    conn.send(data.encode())
                    retry = 2  # Reset retry counter
                    break
                else:
                    echo_stat(f, "I2C Sensor read failure, sending err(0),-1,-1 to client")
                    data = "-1,-1,-1"
                    conn.send(data.encode())
                    echo_stat(f, "Delaying " + str(retry) + " seconds before retry")
                    time.sleep(retry)
                    retry = retry + 1
            except socket.error as msg:
                echo_stat(f, "Client (" + str(addr) + "): connection closed")
                conn.close()
                break
        elif data[0:1] == b't':
            timeStr = data[2:]
            print('I need to set the time')
            print(timeStr)
            data = "0,0,0"
            conn.send(data.encode())
            # conn.close() # close server connection now

# Below except clause will never be executed with python3; not sure about python2
#        except IOError:
#            echo_stat(f, "I2C sensor IO error, sending err(1),-1,-1 to client")
#            data = "-2,-1,-1"
#            conn.send(data.encode())
#            echo_stat(f, "Delaying " + str(retry) + " seconds before retry")
#            time.sleep(retry)
#            retry = retry + 1
#            break

