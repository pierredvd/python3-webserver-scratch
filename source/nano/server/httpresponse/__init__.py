#!/usr/bin/env python3

from nano.server.socketwrapper  import SocketWrapper
from nano.event                 import Event

from collections.abc import Callable

"""
    Class for format http request
"""
class HttpResponse():

    """
        Constructor
        @returns None
    """
    def __init__(self):
        self._event      = Event()
        self.code        = None
        self.protocol    = None
        self.ssl         = False
        self.version     = None
        self.headers     = {}
        self.body        = ""

    """
        Send response
        @returns None
    """
    def send(self):
        self._event.fire("send", {"response": self})

    """
        Add event listener
        @param   eventName str      Name of event to listen
        @param   callback  Callable Callback of event
        @returns None
    """
    def on(self, eventName:str, callback: Callable):
        self._event.on(eventName, callback)