import network
import logging
import machine
import utime
import uasyncio as asyncio

# Logging initialisation
log = logging.getLogger(name="WiFi.py", folder="/logs/", filename="WiFi.log", max_file_size=1000)

class WiFi_AP:
    def __init__(self, ssid, passwd, device_ip):

        self.ssid = ssid
        self.passwd = passwd
        
        log.info("Creating AP with SSID: " + self.ssid)
        self.ap = network.WLAN(network.AP_IF) # create access-point interface
        self.setActive()         # activate the interface
        self.ap.config(essid=self.ssid, password=self.passwd) # set the ESSID of the access point
        log.info("AP Active")

    def setActive(self, active=True):
        self.ap.active(active)

    def isActive(self):
        return self.ap.active()
    
    def isConnected(self):
        return self.ap.isconnected()

class WiFi_STA:
    def __init__(self, ssid, passwd, max_retry_ct, hostname):
    
        self.ssid = ssid
        self.passwd = passwd
        self.hostname = hostname
        self.max_retry_ct = max_retry_ct

        self.station = network.WLAN(network.STA_IF) # create station interface
        self.station.active(True) # activate the interface



    def scan(self):
        log.info("Scanning WiFi networks")
        nets_list = self.station.scan() # list of available networks
        self.available_ssids = [
            {"ssid":name.decode('utf-8'),
            "channel":channel,
            "RSSI":RSSI, "authmode":authmode,
            "hidden":hidden
            } for name, _, channel, RSSI, authmode, hidden in nets_list]
        # log.info(self.available_ssids)
        log.info("WiFi networks scanned succesfully")
        return self.available_ssids

    def getAvailableSSIDS(self):
        try:
            log.info("getting available ssids")
            return self.available_ssids
        except:
            log.info("could not get available ssids")
            return []

    def setCredentials(self, ssid, password):
        log.info("Setting WiFi credentials")
        self.ssid = ssid
        self.passwd = password
        
    def setHostname(self, hostname):
        self.hostname = hostname

    def connect(self):
        log.info("Trying to connect to scanned WiFi network")
        try:
            self.station.config(dhcp_hostname=self.hostname)
            log.info("Scanning")
            nets = self.scan() # list of available networks
            for net in nets:
                ssid = net["ssid"]
                log.info("Comparing {} with {}".format(ssid, self.ssid))
                if ssid == self.ssid:
                    self.station.connect(ssid, self.passwd)
                    num_of_fails = 0
                    while not self.station.isconnected():
                        num_of_fails += 1
                        log.info(".")
                        utime.sleep(1)
                        if num_of_fails > self.max_retry_ct:
                            log.info("Couldn't connect to WLAN, resetting")
                            self.station.disconnect()
                            return -1
                            # machine.reset()
                    log.info('WLAN connection succeeded!')
                    log.info("Successfully connected to WiFi network.")
                    log.info("Device IP: " + str(self.station.ifconfig()[0]))
                    log.info("Subnet Mask: " + str(self.station.ifconfig()[1]))
                    log.info("Gateway IP: " + str(self.station.ifconfig()[2]))
                    return 1
                    # mdns.start('mPy', 'MicroPython ESP32')
                    # ftp.start(user='user', password='Labora_12345')
                    # telnet.start(user='YOUR_USERNAME', password='YOUR_PASSWORD')
                else:
                    log.info("ssid doesn't match, trying next one")
            log.info("NONE of the ssids matched, returning -2")
            return -2
                    
        except OSError as e:
            log.error("WiFi error: %s" % e)
            self.station.disconnect()
            return -3

        else:
            log.warning("Couldn't find network " + self.ssid)
            self.station.disconnect()
            return -4

    def setActive(self, active=True):
        self.station.active(active)

    def get_IP(self):
        return self.station.ifconfig()[0]