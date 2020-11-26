#TIME
from machine import RTC, Pin, I2C
from ds3231 import DS3231

class DS3231_RTC:
    def __init__(self):
        self.rtc = RTC()
        scl_pin = Pin(5, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)
        sda_pin = Pin(4, pull=Pin.PULL_UP, mode=Pin.OPEN_DRAIN)

        i2c = I2C(-1, scl=scl_pin, sda=sda_pin)
        self.ds3231 = DS3231(i2c, self.rtc)

        print("rtc:{}".format(self.rtc.datetime()))
        print("ds3231:{}".format(self.ds3231.get_time()))

    def setTime(self, time):
         # First set integrated rtc time
            self.rtc.datetime(time)
            # Sync rtc time with rtc time
            self.ds3231.save_time()

    def getTime(self):
        return self.ds3231.get_time()
       