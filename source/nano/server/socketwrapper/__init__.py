
from nano.event import Event

import socket
import threading
from collections.abc import Callable
import ssl as libssl
import errno
import sys
import time

"""
    Class for socket wrapping (expect http or websocket protocol)
"""
class SocketWrapper(threading.Thread):

    instances = 0

    """
        Constructor
        @param socket   socket.socket  Socket to wrap
        @param port     int            Incoming socket port 
        @param ssl      bool           if protocol over ssl
        @returns None
    """
    def __init__(self, socket: socket.socket, port: int, ssl: bool):
        type(self).instances = (type(self).instances + 1) % 65535
        self._name      = "SocketProtoWrapper#"+str(type(self).instances)
        self._socket    = socket
        self._local     = socket.getpeername()
        self._remote    = socket.getsockname()
        self._port      = port
        self._ssl       = ssl
        self._event     = Event()
        self._buffer    = b''
        self.closed     = False
        self.terminator = b'\r\n\r\n'
        threading.Thread.__init__(self)

    """
        Destructor
        @returns None
    """
    def __del__(self):
        self.closed     = True

    """
        Hash, for makes object hashable
        @returns None
    """
    def __hash__(self):
        return hash(self._name)

    """
        Eq, for makes object hashable
        @returns None
    """
    def __eq__(self, other):
        return self._name==other._name

    """
        Routine of threading.Thread
        @returns None
    """
    def run(self):
        self._socket.setblocking(0)
        while not self.closed:
            if self._socket.fileno()<0:
                self.closed = True
                break
            try:
                data = self._socket.recv(4096)
                if len(data)>0:
                    self._buffer = self._buffer + data
                    if self.terminator==None or self._buffer.endswith(self.terminator):
                        self._event.fire("data", { "socket": self, "port": self._port, "ssl": self._ssl, "data": self._buffer })
                        self._buffer = b''
                # No need to hard loop to collect socket data 
                # ( 4096b / 0.0039s > 1Mb / s), will not allow more
                time.sleep(0.0039) 
            except BlockingIOError:
                # No data
                continue
            except libssl.SSLWantReadError:
                # No data
                continue
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    continue
                else:
                    self._event.fire("error", { "socket": self._socket, "port": self._port, "ssl": self._ssl, "exception": e })
                    self._socket.shutdown(2)
                    break

        self.close()
        sys.exit(0)

    """
        Force socket to keepalive
        @param   value  bool  Enable keepalive
        @returns None
    """
    def setkeepalive(self, value):
        if value:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        else:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 0)

    """
        Write data on socket
        @param   bytes   data
        @returns None
    """
    def write(self, data: bytes):
        if not self.closed:
            self._socket.send(data)

    """
        Write data on socket and close
        @param   bytes   data
        @returns None
    """
    def end(self, data: bytes):
        if not self.closed:
            self._socket.send(data)
            self.closed = True
            self._event.fire("close", { "socket": self._socket, "port": self._port, "ssl": self._ssl})
            self._socket.close()

    """
        Close socket
        @returns None
    """
    def close(self):
        if not self.closed:
            self.closed = True
            self._event.fire("close", { "socket": self._socket, "port": self._port, "ssl": self._ssl})
            self._socket.close()

    """
        Add event handler
        @returns None
    """
    def on(self, eventName: str, callback: Callable):
        self._event.on(eventName, callback)