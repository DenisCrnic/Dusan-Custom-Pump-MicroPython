from machine import Pin, Timer
# ASYNCIO MODULE
from time import sleep
import logging
import DS3231_RTC
rtc = DS3231_RTC.DS3231_RTC()

# Logging initialisation
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(name="main.py", folder="/logs/", filename="main.log", max_file_size=1500, del_line_num=10)
import ujson
import WiFi
from ws_server import WebSocketServer
from ws_connection import ClientClosedError


class main:
    def __init__(self):
        self.relay2_state = True
        #########################################################################
        ############################## SETTINGS #################################
        #########################################################################
        boot_config = open("boot_config.json") # Opens boot_config.json
        boot_config_string = boot_config.read() # Reads boot_config.json into boot_config_string
        self.boot_config_dict = ujson.loads(boot_config_string) # Parses boot_config_string into Python dictionary
        boot_config.close()

        # SYSTEM
        self.time1 = self.boot_config_dict['system']['time1']
        self.time2 = self.boot_config_dict['system']['time2']
        self.time3 = self.boot_config_dict['system']['time3']
        self.offTime1 = self.boot_config_dict['system']['offTime1']
        self.offTime2 = self.boot_config_dict['system']['offTime2']
        self.offTime3 = self.boot_config_dict['system']['offTime3']
        self.offTime4 = self.boot_config_dict['system']['offTime4']
        self.loopInterval = self.boot_config_dict['system_adv']['loopInterval']
        self.heartbeat_min = self.boot_config_dict['system_adv']['heartbeat_min']
        self.ap_on_time = self.boot_config_dict['system_adv']['ap_on_time']
        self.afterMid = False
        if self.time3 < self.time1:
            #print("3rd time si aftermidnight")
            self.afterMid = True

        # NETWORK
        # AP
        self.AP_SSID = self.boot_config_dict['network']['ap']['AP_SSID']
        self.AP_PASSWORD = self.boot_config_dict['network']['ap']['AP_PASSWORD']
        self.DEVICE_IP = self.boot_config_dict['network']['ap']['AP_IP']
        self.wifi_ap = WiFi.WiFi_AP(self.AP_SSID, self.AP_PASSWORD, self.DEVICE_IP)
        self.wifi_ap.setActive(False)

        # WebREPL
        self.WEB_REPL_ACTIVE = self.boot_config_dict['webrepl']['WEB_REPL_ACTIVE']
        self.WEB_REPL_PASSWORD = self.boot_config_dict['webrepl']['WEB_REPL_PASSWORD']

        #HARDWARE
        self.RELAY_1 = self.boot_config_dict['hardware']['RELAY_1']
        self.RELAY_2 = self.boot_config_dict['hardware']['RELAY_2']
        self.LED_R = self.boot_config_dict['hardware']['LED_R']
        self.LED_G = self.boot_config_dict['hardware']['LED_G']
        self.relay1 = Pin(self.RELAY_1, Pin.OUT)
        self.relay1.value(0)
        self.relay2 = Pin(self.RELAY_2, Pin.OUT)
        self.relay2.value(0)
        self.led_r = Pin(self.LED_R, Pin.OUT)
        self.led_g = Pin(self.LED_G, Pin.OUT)
        self.led_r.value(0)
        self.led_g.value(0)
        self.ap_button = Pin(self.boot_config_dict['hardware']['AP_PIN'], Pin.IN)

        # MAIN LOOP
        self.mainLoop()
        

    def mainLoop(self):
        count = 0
        while True:
            if count > self.heartbeat_min*60 / self.loopInterval:
                count = 0
                log.info("~")
            count += 1
            self.led_g.value(1)
            self.time = rtc.getTime()
            #print(self.time, end =" ")
            interval = self.getInterval()
            self.handleRelay(interval)
            self.led_g.value(0)
            if self.ap_button.value():
                self.led_g.value(1)
                self.wifi_ap.connect()
                i=0
                while not self.wifi_ap.isConnected():
                    i += 1
                    sleep(0.1)
                    if i > self.ap_on_time * 10:
                        break
                if self.wifi_ap.isConnected():
                    self.led_g.value(1)
                    self.led_r.value(1)
                    log.info("Param mode")
                    self.wsServer = WebSocketServer("", self.ws_callback, max_connections=1) # initialising ws server 
                    self.wsServer.start()
                    sleep(0.1)
                    while self.wifi_ap.isConnected(): # ap connection means parametrization mode is in progress
                        self.wsServer.process_all()
                        # #print("#", end=" ")
                    self.wsServer.stop()
                    self.wifi_ap.setActive(False)
                    log.info("Param mode stop")
                    self.led_g.value(0)
                    self.led_r.value(0)
            else:
                sleep(self.loopInterval)



    def wsSend(self, res_dict_id, response_list, conn):
        res_dict = dict()
        res_dict[res_dict_id] = response_list
        response = ujson.dumps(res_dict)
        #print("Sending to client: \n {}".format(response))
        conn.write(response)

    
    # Accept commands sent over web socket (used for initial WiFi parametrization)
    # cmd = command
    # msg = dictionary that is converted to json for easier use
    def ws_callback(self, cmd, msg, conn):
        #print("WS Callback")
        #print(cmd)
        #print(msg)
        res_dict_id = ""
        if cmd == "TIME":
            time=(
                msg[cmd]['year'],
                msg[cmd]['month'],
                msg[cmd]['day'],
                0,
                msg[cmd]['hour'],
                msg[cmd]['minute'],
                msg[cmd]['second'],
                0
            )
            rtc.setTime(time)
            response_list = self.boot_config_dict['system']
            res_dict_id = "SETTINGS"
            self.wsSend(res_dict_id, response_list, conn)

        elif cmd == "SETTINGS":
            with open("boot_config.json", "r") as boot_config:
                boot_config_string = boot_config.read() # Reads boot_config.json into boot_config_string
                self.boot_config_dict = ujson.loads(boot_config_string) # Parses boot_config_string into Python dictionary
                boot_config.close()
            
            self.boot_config_dict['system']['time1']=msg[cmd]['time1']  
            self.boot_config_dict['system']['time2']=msg[cmd]['time2']  
            self.boot_config_dict['system']['time3']=msg[cmd]['time3']  
            self.boot_config_dict['system']['offTime1']=msg[cmd]['offTime1']  
            self.boot_config_dict['system']['offTime2']=msg[cmd]['offTime2']  
            self.boot_config_dict['system']['offTime3']=msg[cmd]['offTime3']  
            self.boot_config_dict['system']['offTime4']=msg[cmd]['offTime4']  
            
            with open("boot_config.json", "w") as boot_config:
                boot_config_string = ujson.dumps(self.boot_config_dict)
                boot_config.write(boot_config_string)
                boot_config.close()
            
            self.time1 = self.boot_config_dict['system']['time1']
            self.time2 = self.boot_config_dict['system']['time2']
            self.time3 = self.boot_config_dict['system']['time3']
            self.offTime1 = self.boot_config_dict['system']['offTime1']
            self.offTime2 = self.boot_config_dict['system']['offTime2']
            self.offTime3 = self.boot_config_dict['system']['offTime3']
            self.offTime4 = self.boot_config_dict['system']['offTime4']

            response_list = self.boot_config_dict['system']
            res_dict_id = "SETTINGS"
            self.wsSend(res_dict_id, response_list, conn)

    def getInterval(self):
        # #print("hour = {}, minute = {}".format(self.time[4], self.time[5]))
        hour = self.time[3]
        var = 0
        if (self.afterMid):
            if (self.time3 <= hour and hour < self.time1):
                # log.info("inside interval 1")
                var = 1
            
            if (self.time1 <= hour and hour < self.time2):
                # log.info("inside interval 2")
                var = 2
            
            if (self.time2 <= hour or hour < self.time3):
                # log.info("inside interval 3")
                var = 3
        
        else:
            if (self.time3 <= hour or hour < self.time1):
                # log.info("inside interval 1_")
                var = 1
            
            if (self.time1 <= hour and hour < self.time2):
                # log.info("inside interval 2_")
                var = 2
            
            if (self.time2 <= hour and hour < self.time3):
                # log.info("inside interval 3_")
                var = 3
        return var

    def handleRelay(self, interval):
        minute = self.time[4]
        #trim minutes
        while (minute >= 15):
            minute -= 15        
        # log.info("new minute: {}".format(minute))
        #rele 1
        if interval == 1:
            if (15 - self.offTime1 > minute):
                self.relay1.value(1)
            else:
                self.relay1.value(0)

        elif interval == 2:
            if (15 - self.offTime2 > minute):
                self.relay1.value(1)
            else:
                self.relay1.value(0)
        elif interval == 3:
            if (15 - self.offTime3 > minute):
                self.relay1.value(1)
            else:
                self.relay1.value(0)
        else:
            log.error("Unknown interval (handleRelay()): {}".format(interval))
        
        # rele 2
        #print("minute {}, relay state {}".format(minute, self.relay2_state))
        if minute == 1 and self.relay2_state:
            #print("min = 1")
            self.relay2_state = False
            self.relay2.value(1)
            timeout = self.offTime4 * 1000
            tim1 = Timer(1)
            tim1.init(period=timeout, mode=Timer.ONE_SHOT, callback=self.relay2Callback)
        elif minute == 15:
            self.relay2_state = True
    
    def relay2Callback(self, x):
        #print(x)
        self.relay2.value(0)

main = main()