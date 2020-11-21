from machine import RTC, Pin
# ASYNCIO MODULE
import uasyncio as asyncio
loop = asyncio.get_event_loop() # Asyncio loop initialisation

import logging
# Logging initialisation
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(name="main.py", folder="/logs/", filename="main.log", max_file_size=2000)
import ujson

class main:
    def __init__(self):
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
        self.afterMid = False
        if self.time3 < self.time1:
            print("3rd time si aftermidnight")
            self.afterMid = True

        # NETWORK
        # AP
        self.AP_SSID = self.boot_config_dict['network']['ap']['AP_SSID']
        self.AP_PASSWORD = self.boot_config_dict['network']['ap']['AP_PASSWORD']
        self.DEVICE_IP = self.boot_config_dict['network']['ap']['AP_IP']

        # WebREPL
        self.WEB_REPL_ACTIVE = self.boot_config_dict['webrepl']['WEB_REPL_ACTIVE']
        self.WEB_REPL_PASSWORD = self.boot_config_dict['webrepl']['WEB_REPL_PASSWORD']

        # NTP
        self.NTP_SYNC_ACTIVE = self.boot_config_dict['ntp']['NTP_SYNC_ACTIVE']
        self.NTP_HOST = self.boot_config_dict['ntp']['NTP_HOST']
        self.NTP_SYNC_PERIOD_S = self.boot_config_dict['ntp']['NTP_SYNC_PERIOD_S']

        #HARDWARE
        self.RELAY_1 = self.boot_config_dict['hardware']['RELAY_1']
        self.RELAY_2 = self.boot_config_dict['hardware']['RELAY_2']
        self.relay1 = Pin(self.RELAY_1, Pin.OUT)

        log.info("start")
        ############################################################################
        ############################# NTP SYNC OVER WIFI ###########################
        log.info(self.NTP_SYNC_ACTIVE)
        if self.NTP_SYNC_ACTIVE:
            import WiFi
            wifi_sta = WiFi.WiFi_STA("Lokavec moj doma", "mackaimastirinoge", 10, "mojapumpa.local")
            wifi_sta.connect()
            import untptime as ntptime
            loop.create_task(ntptime.sync_ntp(period_s=5, host="time.ijs.si")) # set the rtc datetime from the remote server
        ############################################################################
        

        self.rtc = RTC()
        loop.create_task(self.mainLoop())
        loop.create_task(self.wsLoop())

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            log.info("closing")
            loop.close()

    async def mainLoop(self):
        while True:
            self.time = self.rtc.datetime()
            log.info(self.time)
            interval = self.getInterval()
            log.info("Got interval: {}".format(interval))
            self.handleRelay(interval)
            log.info("Relays handled. Relay 1 state: {}".format(self.relay1.value()))


            print(self.boot_config_dict["system"])


            await asyncio.sleep(self.loopInterval)

    async def wsLoop(self):
        import WiFi
        from ws_server import WebSocketServer
        from ws_connection import ClientClosedError
        wifi_ap = WiFi.WiFi_AP(self.AP_SSID, self.AP_PASSWORD, self.DEVICE_IP)

        while True:
            if wifi_ap.isConnected():
                log.info("Client connected to ap, parametrisation mode enable")
                self.wsServer = WebSocketServer("", self.ws_callback, max_connections=1) # initialising ws server 
                self.wsServer.start()
                log.info("WS started")
                while wifi_ap.isConnected(): # ap connection means parametrization mode is in progress
                    log.info("1")
                    self.wsServer.process_all()
                    log.info("2")
                    # await asyncio.sleep(0.05)
                    log.info("3")
                log.info("AP parametrization mode ended")
                self.wsServer.stop()
            else:
                log.info("No clients on AP")
            await asyncio.sleep(3)

    def wsSend(self, res_dict_id, response_list, conn):
        res_dict = dict()
        res_dict[res_dict_id] = response_list
        response = ujson.dumps(res_dict)
        log.info("Sending to client: \n {}".format(response))
        conn.write(response)

    
    # Accept commands sent over web socket (used for initial WiFi parametrization)
    # cmd = command
    # msg = dictionary that is converted to json for easier use
    async def ws_callback(self, cmd, msg, conn):
        log.info("WS Callback")
        
        res_dict_id = ""
        # station wifi scans available networks and sends list of dictionaries as response
        # each dict is one WiFi connection

        # Recieve credentials for station WiFi, try to connect and notify client of conn status
        if cmd == "HELLO":
            # log.info("Got WiFi credentials from client")
            # log.info("MSG: {}".format(msg))
            # log.info("MSG type: {}".format(type(msg)))
            response_list = self.boot_config_dict['system']

            res_dict_id = "SETTINGS"
            self.wsSend(res_dict_id, response_list, conn)

        elif cmd == "SETTINGS":
            with open("boot_config.json", "r") as boot_config:
                boot_config_string = boot_config.read() # Reads boot_config.json into boot_config_string
                boot_config_dict = ujson.loads(boot_config_string) # Parses boot_config_string into Python dictionary
                boot_config.close()

            self.boot_config_dict['system']['time1'] = self.time1
            self.boot_config_dict['system']['time2'] = self.time2
            self.boot_config_dict['system']['time3'] = self.time3
            self.boot_config_dict['system']['offTime1'] = self.offTime1
            self.boot_config_dict['system']['offTime2'] = self.offTime2
            self.boot_config_dict['system']['offTime3'] = self.offTime3
            self.boot_config_dict['system']['offTime4'] = self.offTime4
            
            with open("boot_config.json", "w") as boot_config:
                boot_config_string = ujson.dumps(boot_config_dict)
                boot_config.write(boot_config_string)
                boot_config.close()

            response_list = dict()
            res_dict_id = "SUCCESS"
            self.wsSend(res_dict_id, response_list, conn)




    
    def getInterval(self):
        log.info("hour = {}, minute = {}".format(self.time[4], self.time[5]))
        hour = self.time[4]
        var = 0
        if (self.afterMid):
            if (self.time3 <= hour and hour < self.time1):
                log.info("inside interval 1")
                var = 1
            
            if (self.time1 <= hour and hour < self.time2):
                log.info("inside interval 2")
                var = 2
            
            if (self.time2 <= hour or hour < self.time3):
                log.info("inside interval 3")
                var = 3
            
        
        else:
            if (self.time3 <= hour or hour < self.time1):
                log.info("inside interval 1_")
                var = 1
            
            if (self.time1 <= hour and hour < self.time2):
                log.info("inside interval 2_")
                var = 2
            
            if (self.time2 <= hour and hour < self.time3):
                log.info("inside interval 3_")
                var = 3
        return var

    def handleRelay(self, interval):
        minute = self.time[5]
        sec = self.time[6]
        timer = 90 - self.offTime4
        #trim minutes
        while (minute >= 15):
            minute -= 15
        
        if (minute == 1):
            sec += 60
        
        log.info("new minute: {}".format(minute))
        log.info("new second: {}".format(sec))
        log.info(sec)
        #rele 1
        if interval == 1:
            if (15 - self.offTime1 > minute):
                self.relay1.value(1)
                return
            self.relay1.value(0)

        elif interval == 2:
            if (15 - self.offTime2 > minute):
                self.relay1.value(1)
                return
            self.relay1.value(0)
        elif interval == 3:
            if (15 - self.offTime3 > minute):
                self.relay1.value(1)
                return
            self.relay1.value(0)
        else:
            log.error("Unknown interval (handleRelay()): {}".format(interval))
        
        # rele 2
        # if (minute < 2):
        #     if (minute == 0 and sec == 0):
        #         timer = 90 - self.offTime4
            
        #     if (timer - sec > 0):
        #         digitalWrite(RELE_PIN_2, HIGH)
        #         return
            
        #     digitalWrite(RELE_PIN_2, LOW)
        
    
    



main = main()