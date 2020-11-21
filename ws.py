from ws_connection import ClientClosedError
from ws_server import WebSocketClient
from ws_multiserver import WebSocketMultiServer
import ujson

class TestClient(WebSocketClient):
    def __init__(self, conn, wifi):
        super().__init__(conn)
        self.wifi = wifi

    def process(self):
        try:
            msg = self.connection.read()
            if not msg:
                return
            msg = msg.decode("utf-8")
            print("WS MESSAGE RAW:")
            print(msg)
            cmd = ujson.loads(msg)

            # items = msg.split(" ")
            # cmd = items[0]
            print("WS MESSAGE CONTENT:")
            print(cmd)
            if getList(cmd)[0] == "scan":
                print("SCANNED NETWORKS IN A LIST:")
                nets_list = list(self.wifi.scan())
                response_dict_id = dict()
                response_list = [{"ssid":name.decode('utf-8'), "channel":channel, "RSSI":RSSI, "authmode":authmode, "hidden":hidden} for name, _, channel, RSSI, authmode, hidden in nets_list]
                # for name, _, channel, RSSI, authmode, hidden in nets_list:
                #     print("ssid: {}, channel: {}, RSSI: {}, authmode: {}".format(name.decode('utf-8'), channel, RSSI, authmode))
                #     response_dict[] = {"ssid":name.decode('utf-8'), "channel":channel, "RSSI":RSSI, "authmode":authmode, "hidden":hidden}
                # response_dict_id["SSIDS"] = response_list
                
                # print("_________RESPONSE JSON____________")
                # response = '"SSIDS":{}}'.format(str(response_list))
                response_dict_id["SSIDS"] = response_list
                response = ujson.dumps(response_dict_id)
                print(response)
                self.connection.write(response)
                print("Hello World")

            elif getList(cmd)[0] == "credentials":
                print("ssid:{} passwd:{}".format(cmd["credentials"]["ssid"], cmd["credentials"]["password"]))
                self.wifi.setCredentials(cmd["credentials"]["ssid"], cmd["credentials"]["password"])
                conn_status = self.wifi.connect()
                if (not conn_status):
                    self.connection.write("Successful")
                elif (conn_status == -1):
                    print(conn_status)
                elif (conn_status == -2):
                    print(conn_status)

        except ClientClosedError:
            print("ERROR: ClientClosedError")
            self.connection.close()

        except ValueError as error:
            print("command was not correctly formated")
            


class TestServer(WebSocketMultiServer):
    def __init__(self, wifi):
        super().__init__("test.html", 10)
        self.wifi = wifi

    def _make_client(self, conn):
        return TestClient(conn, self.wifi)

def getList(dict): 
    list = [] 
    for key in dict.keys(): 
        list.append(key) 
          
    return list
