
#!/usr/bin/env python3

from nano.config                    import Config
from nano.event                     import Event
from nano.server.socketportlistener import SocketPortListener
from nano.server.socketwrapper      import SocketWrapper
from nano.server.httpprotocol       import HttpProtocol

from collections.abc import Callable
import os
import ssl as libssl

"""
    Class for manage http servers (request/response)
"""
class Server():

    """
        Constructor, start server listener from configuration
        @param   dirRoot         str    DirRoot of project
        @returns None
    """
    def __init__(self, dirRoot: str):
        self.DS         = os.path.sep
        self.dirRoot    = dirRoot
        self.event      = Event()
        self.config     = Config(self.dirRoot+"config")
        self.vhosts     = self.config.get("vhost", [])
        self.listeners  = set()
        self.sockets    = set()
        self.protocol   = HttpProtocol(self.dirRoot, self.config)

        # Listen data on connexion
        def ondata(args):
            (request, response) = self.protocol.parse(args["socket"], args["port"], args["ssl"], args["data"])
            if request != None and response!=None:

                # Request is valid and not auto managed
                socket = args["socket"]
                def onresponse(args):
                    response    = args["response"]
                    raw         = self.protocol.pack(response)
                    if "connexion" in response.headers and response.headers["connexion"]=="keep-alive":
                        socket.write(raw)
                    else:
                        socket.end(raw)
                
                response.on("send", onresponse)
                self.event.fire("request", {"request": request, "response": response})

        # Listen connexion on port
        def receiveSocket(args):
            socket, port, ssl = args["socket"], args["port"], args["ssl"]
            swp = SocketWrapper(socket, port, ssl)
            swp.on("error"    , lambda args: print("Receive socket error: "+str(args["exception"])))
            swp.on("close"    , lambda args: socket in self.sockets and self.sockets.remove(socket))
            swp.on("data"     , ondata)
            swp.start()
            self.sockets.add(swp)

        # Listen port
        def listenPort(usage):
            port, ssl, wrapper = usage["port"], usage["ssl"], usage["wrapper"]
            spl = SocketPortListener(port, ssl, wrapper)
            spl.on("close"    , lambda args: spl in self.listeners and self.listeners.remove(spl))
            spl.on("error"    , lambda args: print("Listen port error: "+str(args["exception"])))
            spl.on("listen"   , lambda args: print(f"Server is now listening port {args['port']}"))
            spl.on("connect"  , receiveSocket)
            spl.listen()
            self.listeners.add(spl)

        # Read vhost port usage and start servers
        for usage in self._vhost2portsusage(self.vhosts):
            listenPort(usage)

    """
        Add event listener
        @param   eventName  str         EventName
        @param   callback   Callable    Callback
        @returns None
    """
    def on(self, eventName: str, callback: Callable):
        self.event.on(eventName, callback)

    """
        Destructor, cleans up
        @returns None
    """
    def __del__(self):
        for socket in self.sockets:
            sockets.close()
        self.sockets    = set()
        for listener in self.listeners:
            listener.close()
        self.listeners  = set()

    """
        Convert vhost config to portUsage config
        @param   vhosts list    List of vhosts given by configuration
        @returns None
    """
    def _vhost2portsusage(self, vhosts: list):
        ports = []
        for vhost in vhosts:

            if "port" in vhost and not vhost["port"] in ports:
                wrapper = lambda sock: sock
                ssl = False
                if "ssl" in vhost and vhost["ssl"]!=None:
                    if not "certfile" in vhost["ssl"]:
                        raise Exception("Sll config requires \"certfile\" attribute")

                    certfilepath = os.path.abspath(vhost["ssl"]["certfile"])
                    if not os.path.isfile(certfilepath):
                        raise Exception("Sll \"certfile\" not found at \""+vhost["ssl"]["certfile"]+"\"")

                    if not "keyfile" in vhost["ssl"]:
                        raise Exception("Sll config requires \"keyfile\" attribute")

                    keyfilepath = os.path.abspath(vhost["ssl"]["keyfile"])
                    if not os.path.isfile(keyfilepath):
                        raise Exception("Sll \"keyfile\" not found at \""+vhost["ssl"]["keyfile"]+"\"")

                    ssl = True

                    wrapper = lambda sock: libssl.wrap_socket(sock, server_side=True, certfile=certfilepath, keyfile=keyfilepath)
                ports.append({"port": int(vhost["port"]), "ssl": ssl, "wrapper": wrapper })
        return ports
