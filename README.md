# tpMonitor.py
(Written for Python 2)

Python monitor script to connect to tpServer 

This script will periodically request temperature and pressure (converted to depth) from a server script running on a Raspberry Pi. 

Usage: tpMonitor.py <fname>  Where <fname> is the file used to store the data.
NOTE    : If <fname> already exists, new data will be appended to it.
NOTE(2) :tpMonitor.py expects the init file 'tpMonitor.ini' within the root directory
