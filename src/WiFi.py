import network

class WiFi_AP:
    def __init__(self, ssid, passwd, device_ip):
        self.ssid = ssid
        self.passwd = passwd
        self.ap = network.WLAN(network.AP_IF) # create access-point interface
        
        # ap.config(essid="drek123", password="asdfasdf", authmode=network.AUTH_WPA_WPA2_PSK)
        

    def setActive(self, active=True):
        self.ap.active(active)

    def isActive(self):
        return self.ap.active()
    
    def isConnected(self):
        return self.ap.isconnected()
    
    def connect(self):
        self.setActive(True)         # activate the interface
        self.ap.config(essid=self.ssid, password=self.passwd, authmode=network.AUTH_WPA_WPA2_PSK) # set the ESSID of the access point
        

