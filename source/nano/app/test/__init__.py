#!/usr/bin/env python3

from nano.app.instance           import Instance
from nano.event                  import Event

import threading

"""
    Class for automatized tests
"""
class Test(threading.Thread):

    def __init__(self, parent: Instance):
        self.App    = parent
        self.event  = Event()
        threading.Thread.__init__(self)

    def requireEqual(self, a, b):
        pass

    def requireTrue(self, a):
        pass

    def requireFalse(self, a):
        pass

    def requireNone(self, a):
        pass

    def success(a):
        pass 

    def run(self):
        pass

    def skip(self, a):
        pass 

    def error(self, a):
        pass 