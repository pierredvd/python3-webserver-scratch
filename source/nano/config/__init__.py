#!/usr/bin/env python3

import os
import sys
import json
import time

"""
    Class for manage configuration json directory
"""
class Config:

    """
        List configuration files (json) and save it in a tree
        @param   directoryPath str    Path of main configuration directory
        @returns None
    """
    def __init__(self, directoryPath: str):
        self.DS                 = os.path.sep
        self.directory          = os.path.abspath(directoryPath) + self.DS
        self.data               = {}
        self._lastCheckUpdate   = 0
        self._mtimes            = {}
        self.update()

    """
        Destructor empty internal data
        @returns None
    """
    def __del__(self):
        self.data = None

    """
        Ask update configuration from files
        @returns None
    """
    def update(self):

        # Limit 1 update per sec
        now = int(time.time())
        if self._lastCheckUpdate>=now:
            return
        self._lastCheckUpdate = now

        # Prepare
        start       = 0
        finish      = 0
        name        = ""
        errors      = []
        files       = self._listFiles(self.directory)

        # Check mtimes fur update
        needUpdate = False
        for file in files:
            stat = os.lstat(file)
            key  = str(hash(file))
            if not key in self._mtimes or stat.st_mtime > self._mtimes[key]+1:
                needUpdate = True
                self._mtimes[key] = int(stat.st_mtime)

        if needUpdate:
            # Update
            self.data = {}
            for file in files:
                start   = file.rfind(os.sep)+1
                finish  = file.rfind(".")
                name    = file[start:finish]
                try:
                    fd  = open(file ,mode='r')
                    data= fd.read()
                    fd.close()
                    self.data[name] = json.loads(data)
                except Exception as e:
                    errors.append(str(e))
            if len(errors)>0:
                raise BaseException("\n".join(errors)).with_traceback(sys.exc_info()[2])

    """
        List recursively json files in a directory
        @param   directoryPath str    Path of directory
        @returns None
    """
    def _listFiles(self, directoryPath: str) -> list:
        files = []
        try:
            items = os.listdir(directoryPath)
        except Exception as e:
            return []

        for item in items:
            if os.path.isfile(directoryPath+item):
                files.append(directoryPath+item)
                if os.path.isdir(directoryPath+item):
                    files += self._listFiles(directoryPath+item+self.DS)
        return files

    """
        Get a tree part of configuration from xpath
        @param   xpath          str    Xpath, formed like dir.file.sub.dict.key.level
        @param   defaultValue   any    (facultative) What returnd if no value found 
        @returns value          any    Wanted configration tree part or default value
    """
    def get(self, xpath: str, defaultValue=None) -> str:
        segments = xpath.split('.')
        buffer   = self.data
        index    = 0
        for segment in segments:

            if buffer.__class__.__name__=="list":
                index = self._str2int(segment)
                if index == -1:
                    return defaultValue
                buffer = buffer[index]

            else:
                if not (segment in buffer):
                    return defaultValue
                buffer = buffer[segment]

        return buffer

    """
        Return first level keys of data (list of files)
        @returns list          list    first level keys of data
    """
    def keys(self):
        return list(self.data.keys())

    """
        Check and convert a string to a int
        @param   incoming       str    Given string
        @param   number         int    Extracted number or -1
    """
    def _str2int(self, incoming: str) -> int:
        numeric = "0123456789"
        number  = 0
        pos     = 0
        found   = False
        for char in incoming:
            pos = numeric.find(char)
            if pos >= 0:
                number = number * 10 + pos
                found = True
        if found:
            return number
        return -1
