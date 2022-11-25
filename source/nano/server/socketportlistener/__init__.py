
from nano.event import Event
from collections.abc import Callable

import socket
import threading
import ssl as libssl
import time

"""
    Class for manage port listening (with over ssl wrapped if needed)
"""
class SocketPortListener(threading.Thread):

    """
        Constructor
        @param port     int         Port to listen
        @param ssl      bool        If socket wrapper is over ssl
        @param wrapper  Callable    Socket wrapper for "over" protocol, as ssl
        @returns None
    """
    def __init__(self, port: int, ssl: bool, wrapper: Callable):
        self._socket    = None
        self._name      = "SocketPortListener#"+str(port)
        self._port      = port
        self._ssl       = ssl
        self._wrapper   = wrapper
        self._event     = Event()
        self._listening = False
        threading.Thread.__init__(self)

    """
        Destructor, close current soket
        @returns None
    """
    def __del__(self):
        self.close()

    """
        Hash, to makes class hashable
        @returns None
    """
    def __hash__(self):
        return hash(self._name)

    """
        Eq, to makes class hashable
        @returns None
    """
    def __eq__(self, other):
        return self._name == other._name


    """
        Start port listening
        @returns None
    """
    def listen(self):
        #self._socket = socket.socket()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Listen all incoming ip on port
            self._socket.bind(("0.0.0.0", self._port))
            self._socket.listen(1)
            self._listening = True
            self._event.fire("listen", { "port" : self._port, "ssl": self._ssl})
            self.start()
        except socket.error as e:
            self._event.fire("error", {"exception", e})
            self.close()

    """
        Close listening socket
        @returns None
    """
    def close(self):
        if self._listening:
            if self._socket != None:
                self._socket.close()
                self._socket = None
            self._listening = False
            self._event.fire("close", {"self": self })

    """
        Register a callback to listen an event
        @paran   eventName  str         name of event
        @param   callback   Callable    callback
        @returns None
    """
    def on(self, eventName: str, callback: Callable):
        self._event.on(eventName, callback)

    """
        Main routine of threading.Thread
        @returns None
    """
    def run(self):
        while self._listening:
            try:
                socket, address = self._socket.accept()
                self._event.fire("connect", { "port": self._port, "ssl": self._ssl, "socket": self._wrapper(socket) })
            except libssl.SSLError as e:
                msg = str(e)
                try:
                    pos = msg.index("SSLV3_ALERT_CERTIFICATE_UNKNOWN")
                    pos = msg.index("sslv3 alert certificate unknown")
                    # Ignore it
                except ValueError as n:
                    self._event.fire("error", {"exception", e})
                    sys.exit(1)
                    return
            except Exception as e:
                self._event.fire("error", {"exception", e})
                sys.exit(1)
                return
            # a small sleep break 100% cpu disease, limit 50 incoming socket by second
            time.sleep(0.02)