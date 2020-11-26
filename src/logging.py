import sys
import uos
import uerrno

import DS3231_RTC
rtc = DS3231_RTC.DS3231_RTC()

CRITICAL = 50
ERROR    = 40
WARNING  = 30
INFO     = 20
DEBUG    = 10
NOTSET   = 0

_level_dict = {
    CRITICAL: "CRIT",
    ERROR: "ERROR",
    WARNING: "WARN",
    INFO: "INFO",
    DEBUG: "DEBUG",
}

class logging:

    level = NOTSET

    def __init__(self, name, folder, filename, max_file_size, del_line_num):
        self.name = name
        self.folder = folder
        self.filename = filename
        self.full_path = self.folder + self.filename
        self.max_file_size = max_file_size
        self.del_line_num = del_line_num

    def _level_str(self, level):
        l = _level_dict.get(level)
        if l is not None:
            return l
        return "LVL%s" % level

    def setLevel(self, level):
        self.level = level

    def isEnabledFor(self, level):
        return level >= (self.level or _level)

    def check_log_size(self, log_file, max_log_size):
        while(uos.stat(log_file)[6] > max_log_size):
            # print("Log file is TOO Large")
            # print("Opening original file")
            with open(log_file, 'r') as original_file:
                data = str(original_file.read()).split('\n')
                # print("Closing original file")
                original_file.close()

            # print("Opening new file")
            with open(log_file, 'w') as new_file:
                # print("Writing new file")
                for line in data[self.del_line_num:]:
                    new_file.write(line)
                # print("Closing new file")
                new_file.close()
            # print("OK")

    def log(self, level, msg, *args):
        if level >= (self.level or _level):
            try:
                # print(uos.stat("/main/web_files/log.html")[6])
                self.check_log_size(self.full_path, self.max_file_size)
            except OSError as exc:
                print(exc)
                if exc.args[0] == uerrno.ENOENT:
                    print("File Doesn't exist, creating one")
                    print(self.full_path)
                    temp_file = open(self.full_path, "w")
                    temp_file.close()
                    print("File created succsefully!")
            
            _stream = open(self.full_path, "a+")
            print("[{}][{}][{}]: {}".format(self.get_time(), self._level_str(level), self.name, msg))
            if not args:
                try:
                    print("[{}][{}][{}]: {}".format(self.get_time(), self._level_str(level), self.name, msg), file=_stream)
                except Exception as err:
                    print("Exception: %s", err)
            else: # TUKAJ MI ŠE NI JASNO KAJ IN KAKO
                print(msg % args, file=_stream)
            _stream.close()

    def get_time(self):
        time_formatted = "{}.{}.{} {}:{}:{}".format(str(rtc.getTime()[0]), str(rtc.getTime()[1]), str(rtc.getTime()[0]), str(rtc.getTime()[3]), str(rtc.getTime()[4]), str(rtc.getTime()[5]))
        return time_formatted
    def debug(self, msg, *args):
        self.log(DEBUG, msg, *args)

    def info(self, msg, *args):
        self.log(INFO, msg, *args)

    def warning(self, msg, *args):
        self.log(WARNING, msg, *args)

    def error(self, msg, *args):
        self.log(ERROR, msg, *args)

    def critical(self, msg, *args):
        self.log(CRITICAL, msg, *args)

    def exc(self, e, msg, *args):
        self.log(ERROR, msg, *args)
        sys.print_exception(e, _stream)

    def exception(self, msg, *args):
        self.exc(sys.exc_info()[1], msg, *args)

_level = INFO
_loggers = {}

def getLogger(name, folder, filename, max_file_size, del_line_num=5):
    if name in _loggers:
        return _loggers[name]
    l = logging(name, folder, filename, max_file_size, del_line_num)
    _loggers[name] = l
    return l

def info(msg, *args):
    getLogger(None).info(msg, *args)

def debug(msg, *args):
    getLogger(None).debug(msg, *args)

def basicConfig(level=INFO, filename=None, stream=None, format=None):
    global _level, _stream
    _level = level
    if stream:
        _stream = stream
    if filename is not None:
        print("logging.basicConfig: filename arg is not supported")
    if format is not None:
        print("logging.basicConfig: format arg is not supported")
