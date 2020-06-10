### Installing tpServer as a system process.
Requires the following files:
- **tpServer.py**
- **tpUtilities.py** 
- **ms5837.py**
- **mock_ms5837.py** (optional - for local debugging support)

As root, perform the following steps:
- Install **tpServer.py**, **tpUtilities.py**, and **ms5837.py** in `/etc/systemd/user/tpServer/`
  (This is the accepted location for user service executables)

- Install the file **tpServer.service** in the following directory:
`/usr/etc/systemd/system`
make sure this file is executable:  
 `$ chmod 664 tpServer.service`

- For new installations, you need to let the systemctl manager know about this new service:  
`$ systemctl daemon-reload`  
`$ systemctl enable tpServer.service`

- Reboot the Pi and verify the server is running:  
`$ systemctl status tpServer.service`  
The output should look similar to:  
>● tpServer.service - Server task to send temperature and depth data  
>   Loaded: loaded (/etc/systemd/system/tpServer.service; enabled; vendor preset: enabled)  
>   Active: active (running) since Tue 2020-06-09 08:51:40 CDT; 22h ago  
> Main PID: 493 (python3)  
>    Tasks: 1 (limit: 2200)  
>   Memory: 9.3M  
>   CGroup: /system.slice/tpServer.service  
>           └─493 /usr/bin/python3 -u tpServer.py


A `systemctl` reference can be found [here]: 


[here]: https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units
