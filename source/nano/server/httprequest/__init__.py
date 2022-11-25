#!/usr/bin/env python3

"""
    Class for format http request
"""
class HttpRequest():

    """
        Constructor
        @returns None
    """
    def __init__(self):
        self.scheme      = None
        self.protocol    = None
        self.ssl         = False
        self.version     = None
        self.method      = None
        self.headers     = {}
        self.vhost       = None
        self.post        = {}
        self.files       = {}
        self.get         = {}
        self.cookies     = {}
        self.body        = ""