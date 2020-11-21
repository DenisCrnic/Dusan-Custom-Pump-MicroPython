try:
    import usocket as socket
except:
    import socket
try:
    import ustruct as struct
except:
    import struct
    
import machine
import logging
log = logging.getLogger(name="untptime.py", folder="/logs/", filename="untptime.log", max_file_size=2500)
import utime as time
import uasyncio as asyncio
# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600

# There's currently no timezone support in MicroPython, and the RTC is set in UTC time.
def settime(host):
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    try:
        log.debug(1)
        addr = socket.getaddrinfo(host, 123)[0][-1]
        log.debug(2)
    except:
        log.warning("Can't establish connection with NTP server")
        return -1
    log.debug(3)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # TODO Reprogram fro ASYNC
        log.debug(4)
        s.setblocking(False)
        log.debug(5)
        res = s.sendto(NTP_QUERY, addr)
        log.debug(6)
        log.debug("NTP_QUERY:" + str(NTP_QUERY))
        log.debug("ADDR:" + str(addr))
        retry_count = 0
        while (True):
            try:
                msg = s.recv(48)
                break
            except Exception as e:
                # TODO: TRY 10 times and return error
                log.warning("Didn't recieve a response yet: " + str(e))
                retry_count += 1
                if(retry_count > 10):
                    log.error("No response after 10 retries, returning from function")
                    return -2
                time.sleep(0.1)
        log.debug("MSG:" + str(msg))
    except Exception as e:
        log.error("EXCEPTION: " + str(e))
        return -3

    finally:
        s.close()

    val = struct.unpack("!I", msg[40:44])[0]
    log.debug("val:" + str(val))
    t = val - NTP_DELTA
    tm = time.localtime(t)
    tm = tm[0:3] + (0,) + tm[3:6] + (0,)
    machine.RTC().datetime(tm)
    return 0

# TODO make ntptime module with asyncio
# https://github.com/micropython/micropython/blob/bd7af6151d605d3fc8f70cb9ddf45b2fd7881f08/ports/esp8266/modules/ntptime.py
async def sync_ntp(woff=1,soff=2, period_s=600, host="pool.ntp.org"):
    while True:
        MAX_RETRY_NTP = 20
        log.info("Setting NTP time")
        log.info("Local time before synchronization：" + str(time.localtime()))
        for retry in range(MAX_RETRY_NTP):
            try:
                # loop = asyncio.get_event_loop()
                task = settime(host)
                log.info(task)
                if task == -1:
                    log.error("socket.getaddrinfo error")
                    raise Exception
                    
                if task == -2:
                    log.error("No response error")
                    raise Exception

                if task == -3:
                    log.error("Something went wrong idk what and idc")
                    raise Exception
                t = time.time()
                tm = list(time.localtime(t))
                tm = tm[0:3] + [0,] + tm[3:6] + [0,]
                year = tm[0]

                #Time of March change for the current year
                t1 = time.mktime((year,3,(31-(int(5*year/4+4))%7),1,0,0,0,0))
                #Time of October change for the current year
                t2 = time.mktime((year,10,(31-(int(5*year/4+1))%7),1,0,0,0,0))

                if t >= t1 and t < t2:
                    tm[4] += soff #UTC + 1H for BST
                else:
                    tm[4] += woff #UTC + 0H otherwise

                machine.RTC().datetime(tm)
                log.debug(time.localtime())
                # log.info(machine.RTC().datetime())
                log.info("Time synchronized: " + str(time.localtime()))
                break

            except Exception as e:
                if(retry == MAX_RETRY_NTP - 1):
                    log.info("Couldn't obtain time because: " + str(e))
                    break
                log.info(".")
                await asyncio.sleep(3)
            await asyncio.sleep(0.1)
        await asyncio.sleep(period_s)