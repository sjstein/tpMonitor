#!/usr/bin/python3

import ms5837
import socket
import fcntl
import struct
import time

from datetime import date
from datetime import datetime

s = ''

## Begin function definition 'get_ip_address(ifname)'
##   A function to return the IP number bound to a specific ethernet interface (ifname)
def get_ip_address(ifname):  # Function to return IP# bound to specific interface
    errorCount = 0
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack(b'256s', ifname[:15]))[20:24])

        except:
            time.sleep(1)
            errorCount += 1
            if errorCount > 60:
                raise Exception("Unable to obtain ip# during tpServer start")




## End function definition

## Begin function definition 'statusOutput(fdesc, msg)
def echoStat(fdesc, msg):
    print(("[" + str(datetime.now()) + "] " + msg))
    fdesc.write("[" + str(datetime.now()) + "] " + msg + "\n")


## End function definition


## Delay to allow network interface to come up
## time.sleep(10)

HOST = get_ip_address(b'eth0')  # Determine IP# on eth0
PORT = 5005  # Server port

## Open port to accept remote requests
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)

## Instatiate sensor using default I2C parms
sensor = ms5837.MS5837_30BA()  # Default I2C bus is 1 (Raspberry Pi 3)

fname = str(date.today()) + "_tpServer.log"
f = open(fname, 'a')  # Open log file (append)

echoStat(f, "Server started")
echoStat(f, "Server IP# : " + HOST)
echoStat(f, "Server Port: " + str(PORT))

retry = 2  # Timer for retries

# initialize the sensor
while True:
    try:
        if sensor.init():
            echoStat(f, "I2C Sensor initialized")
            retry = 2  # Reset timer
            break
    except:
        echoStat(f, "Init sensor failed. Retrying after " + str(retry) + " Seconds")
        time.sleep(retry)
        retry = retry + 1

# We have to read initial values from sensor to update pressure and temperature
if not sensor.read():
    echoStat(f, "Initial sensor read failed - exiting")
    exit(1)

echoStat(f, "Initial Pressure: "
         + str(sensor.pressure(ms5837.UNITS_atm)) + " atm, "
         + str(sensor.pressure(ms5837.UNITS_Torr)) + " Torr, "
         + str(sensor.pressure(ms5837.UNITS_psi)) + " psi")

echoStat(f, "Initial Temperature: "
         + str(sensor.temperature(ms5837.UNITS_Centigrade)) + " C, "
         + str(sensor.temperature(ms5837.UNITS_Farenheit)) + " F, "
         + str(sensor.temperature(ms5837.UNITS_Kelvin)) + " K")

freshwaterDepth = sensor.depth()  # default is freshwater
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
saltwaterDepth = sensor.depth()  # No nead to read() again

# NOTE: Leaving density set for saltwater as this is most common use case

echoStat(f, "Initial Depth: "
         + str(freshwaterDepth) + " m (freshwater), "
         + str(saltwaterDepth) + " m (saltwater)")

echoStat(f, "Initial Altitude: "
         + str(sensor.altitude()) + " m")

time.sleep(5)

# Main loop
while True:
    conn, addr = s.accept()
    echoStat(f, "Client connected from IP: " + str(addr))
    while True:
        try:
            if sensor.read():
                pres = sensor.pressure()  # mbar (no arguments)
                #	pres = sensor.pressure(ms5837.UNITS_psi) #  psi
                temp = sensor.temperature()  # degrees C (no arguments)
                #	temp = sensor.temperature(ms5837.UNITS_Farenheit)) #  Farenheit
                dept = sensor.depth()  # Saltwater depth (m)
                data = str(pres) + ',' + str(temp) + ',' + str(dept)
                echoStat(f, "Server sent: " + data)
                conn.send(data.encode())
                retry = 2  # Reset retry counter
                break
            else:
                echoStat(f, "I2C Sensor read failure, sending err(0),-1,-1 to client")
                data = "-1,-1,-1"
                conn.send(data.encode())
                echoStat(f, "Delaying " + str(retry) + " seconds before retry")
                time.sleep(retry)
                retry = retry + 1
        except socket.error as msg:
            echoStat(f, "Client (" + str(addr) + "): connection closed")
            break

        except IOError:
            echoStat(f, "I2C sensor IO error, sending err(1),-1,-1 to client")
            data = "-2,-1,-1"
            conn.send(data.encode())
            echoStat(f, "Delaying " + str(retry) + " seconds before retry")
            time.sleep(retry)
            retry = retry + 1
            break
conn.close()
