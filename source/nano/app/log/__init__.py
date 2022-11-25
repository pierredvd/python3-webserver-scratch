#!/usr/bin/env python3

from nano.server.httprequest       import HttpRequest

import os
import time
import traceback

"""
    Class for app logs
"""
class Log:

    """
        Constructor
        @param directoryPath str  Log directory
        @return None
    """
    def __init__(self, directoryPath: str):
        self.DS                 = os.path.sep
        self.directory          = os.path.abspath(directoryPath) + self.DS
        self._path              = None 
        self._lastCheckUpdate   = 0

    """
        Destructor, close file pointers
        @return None
    """
    def __del__(self):
        pass

    """
        Return current log ath directory (one by each days)
        @return None
    """
    def _logPath(self):

        # Limit 1 update per sec
        now = int(time.time())
        if self._lastCheckUpdate>=now:
            return self.directory + self._path + self.DS
        self._lastCheckUpdate = now

        # Check if day has changed (path of today logs directory)
        today = time.strftime("%Y-%m-%d").replace('-', self.DS)
        if self._path==None or self._path != today:
            self._path = today

            # Create new directory path
            segments = today.split(self.DS)
            path     = self.directory
            for segment in segments:
                path += segment + self.DS
                if not os.path.isdir(path):
                    os.mkdir(path, 0o776)

        return self.directory + self._path + self.DS

    """
        Log Trace
        @param  message str  Message
        @return None
    """
    def trace(self, message: str):
        message = "["+time.strftime("%Y-%m-%d %H:%m:%S")+"] "+message+"\r\n"
        file = open(self._logPath()+'trace.log', "a")
        file.write(message)
        file.close()

    """
        Log Access
        @param  request HttpRequest requete http
        @return None
    """
    def access(self, request: HttpRequest):
        try:
            message  = ' '.join([
                '['+time.strftime("%Y-%m-%d %H:%m:%S")+']',
                request.method.upper(),
                request.scheme+'://'+request.headers["host"]+request.headers["queryString"],
                '@ '+request.headers["remoteHost"]+':'+str(request.headers["remotePort"])+'->'+request.headers["localHost"]+':'+str(request.headers["localPort"])
            ])+"\r\n"
            file = open(self._logPath()+'access.log', "a")
            file.write(message)
            file.close()
        except Exception as e:
            self.error(e)

    """
        Log Errors
        @param  err Exception  Erreur à tracer
        @return None
    """
    def error(self, err: Exception):
        message = err.__class__.__name__.upper()+" "+str(err)+"\r\n"+(''.join(traceback.format_tb(err.__traceback__)))
        print(message)
        message = "["+time.strftime("%Y-%m-%d %H:%m:%S")+"] "+message+"\r\n"
        file = open(self._logPath()+'error.log', "a")
        file.write(message)
        file.close()
