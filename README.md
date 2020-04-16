# Client / server for reading depth(pressure) and temperature data from the BlueRobotics I2C sensor suite connected to a Raspberry Pi

# tpMonitor.py
Python 3.8 / 2.7 compatible

Python monitor script to connect to tpServer 

This script will periodically request temperature and pressure (converted to depth) from a server script running on a Raspberry Pi. 

Type python tpMonitor.py --help for list of arguments

# tpServer.py
Python 3.8 / 2.7 compatible

Server side program to read data from sensor and handle requests from tpMonitor task over network

