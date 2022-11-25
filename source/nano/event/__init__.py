#!/usr/bin/env python3

from collections.abc import Callable

"""
    Class for manage event handlers
"""
class Event:

    """
        Prepare handlers
    """
    def __init__(self): 
        self.handlers = {"*": []}

    """
        Destroy internal memory
    """
    def __del__(self): 
        self.handlers = {"*": []}

    """
        Register a callback to listen an event, "*" for listen all
        @param   eventName str        Name of event to listen
        @param   callback  Callable   callback
        @returns           None
    """
    def on(self, eventName: str, callback: Callable):
        if not (eventName in self.handlers):
            self.handlers[eventName] = []
        self.handlers[eventName].append(callback)

    """
        Fire an event
        @param   eventName str        Name of event to fire
        @param   args      dict       Parameters of event
        @returns           None
    """
    def fire(self, eventName: str, args={}):
        if eventName == "*":
            raise Exception("Event \"*\" fire forbidden")
        if not "event" in args:
            args["event"] = eventName

        if eventName in self.handlers:
            for callback in self.handlers[eventName]:
                callback(args)

        for callback in self.handlers['*']:
            callback(args)

    """
        Stop to listen an event
        @param   eventName str        Name of event to remove listens
        @returns           None
    """
    def off(self, eventName: str):
        if eventName == "*":
            raise Exception("Event \"*\" off forbidden")
        if eventName in self.handlers:
            self.handlers[eventName] = []