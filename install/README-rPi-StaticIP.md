### Set static IP# for raspbian OS
###### Note: this is verified accurate for (at least) raspbian-2018-03-14. The image (_2018-03-13-raspbian-stretch.zip_) can be found [here]


 As user root, perform the following:
 - Edit /etc/dhcpd.conf and add the following to the end of the file:  
 `interface eth0`  
 `static ip_address=<_ip number_>/24`  
 `static routers=192.168.1.1`  
 `static domain_name_servers=192.168.1.1`  

[here]: http://downloads.raspberrypi.org/raspbian/images/raspbian-2018-03-14/