import os
import socket
import network
import websocket_helper
import uselect
from time import sleep
from ws_connection import WebSocketConnection, ClientClosedError
import ujson

# ASYNCIO MODULE
import uasyncio as asyncio

# LOGGING MODULE
import logging
# Logging initialisation
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(name="ws_server.py", folder="/logs/", filename="ws_server.log", max_file_size=5000)

class WebSocketClient:
    def __init__(self, conn, callback):
        self.connection = conn
        self.callback = callback

    def process(self):
        msg = ""
        try:
            
            msg = self.connection.read()
            if not msg == None:
                msg = msg.decode('utf-8')
                log.info("#######################################")
                log.info("WebSocket MSG before json decode: {}".format(msg))
                msg = ujson.loads(msg)
                cmd = self.getList(msg)[0]
                log.info("WebSocket cmd: {}".format(cmd))
                # TODO: rewrite this to work with loop.create_task!
                loop = asyncio.get_event_loop()
                task_ws = loop.create_task(self.callback(cmd, msg, self.connection))
                loop.run_until_complete(task_ws)
                # self.callback(cmd, msg, self.connection)
                
        except ClientClosedError:
            log.error("ClientClosedError")
            self.connection.close()

        except ValueError as error:
            log.error("ValueError")
            pass
        else:
            pass

    def getList(self, dict): 
        list = [] 
        for key in dict.keys(): 
            list.append(key) 
            
        return list
        


class WebSocketServer:
    def __init__(self, page, callback, max_connections=1):
        self._listen_s = None
        self._listen_poll = None
        self._clients = []
        self._max_connections = max_connections
        self._page = page
        self.callback = callback

    def _setup_conn(self, port):
        self._listen_s = socket.socket()
        self._listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_poll = uselect.poll()

        ai = socket.getaddrinfo("0.0.0.0", port)
        addr = ai[0][4]

        self._listen_s.bind(addr)
        self._listen_s.listen(1)
        self._listen_poll.register(self._listen_s)
        for i in (network.AP_IF, network.STA_IF):
            iface = network.WLAN(i)
            if iface.active():
                log.info("WebSocket started on ws://%s:%d" % (iface.ifconfig()[0], port))

    def _check_new_connections(self, accept_handler):
        poll_events = self._listen_poll.poll(0)
        if not poll_events:
            return

        if poll_events[0][1] & uselect.POLLIN:
            # log.info(accept_handler)
            accept_handler()

    def _accept_conn(self):
        cl, remote_addr = self._listen_s.accept()
        ## ADDED LINE for use of ap parametrization in SECCS ##
        # Close previous client since we can only have one client.
        # This works because on ap we accept only one client and NEW client 
        # is the corect one and not previous (in case previous client connected to ap
        # did not close WS connection properly before closing WiFi )
        log.info(1)
        for client in self._clients:
            client.connection.close()

            log.info(2)
        log.info(3)

        log.info("Client connection from: {}".format(remote_addr))

        if len(self._clients) >= self._max_connections:
            # Maximum connections limit reached
            cl.setblocking(True)
            cl.sendall("HTTP/1.1 503 Too many connections\n\n")
            cl.sendall("\n")
            #TODO: Make sure the data is sent before closing
            sleep(0.1)
            cl.close()
            return

        try:
            websocket_helper.server_handshake(cl)
        except OSError:
            # Not a websocket connection, serve webpage
            self._serve_page(cl)
            return

        self._clients.append(self._make_client(WebSocketConnection(remote_addr, cl, self.remove_connection)))

    def _make_client(self, conn):
        wc = WebSocketClient(conn, self.callback)
        return wc

    def _serve_page(self, sock):
        try:
            sock.sendall('HTTP/1.1 200 OK\nConnection: close\nServer: WebSocket Server\nContent-Type: text/html\n')
            length = os.stat(self._page)[6]
            sock.sendall('Content-Length: {}\n\n'.format(length))
            # Process page by lines to avoid large strings
            with open(self._page, 'r') as f:
                for line in f:
                    sock.sendall(line)
        except OSError:
            # Error while serving webpage
            pass
        sock.close()

    def stop(self):
        if self._listen_poll:
            self._listen_poll.unregister(self._listen_s)
        self._listen_poll = None
        if self._listen_s:
            self._listen_s.close()
        self._listen_s = None

        for client in self._clients:
            client.connection.close()
        log.info("Stopped WebSocket server.")

    def start(self, port=80):
        if self._listen_s:
            self.stop()
        self._setup_conn(port)
        log.info("Started WebSocket server.")

    def process_all(self):
        self._check_new_connections(self._accept_conn)

        for client in self._clients:
            client.process()

    def remove_connection(self, conn):
        for client in self._clients:
            if client.connection is conn:
                self._clients.remove(client)
                return