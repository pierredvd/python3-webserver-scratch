#!/usr/bin/env python3

from nano.config                import Config
from nano.event                 import Event
from nano.server.httprequest    import HttpRequest
from nano.server.httpresponse   import HttpResponse
from nano.app.instance          import Instance
from nano.app.controller        import Controller

import os

"""
    Class for manage applicatives
"""
class App():

    """
        Constructor, start server listener from configuration
        @param   dirRoot         str    DirRoot of project
        @param   configDirectory str    Directory of server configuration
        @returns None
    """
    def __init__(self, dirRoot: str):
        self.DS             = os.path.sep
        self.dirRoot        = dirRoot
        self.event          = Event()
        self.config         = Config(self.dirRoot+"config")
        self.vhosts         = self.config.get("vhost", [])
        self.applicatives   = {}
        self._loadApplicatives()

    """
        Load actives applicatives from vhosts configuration
        @returns None
    """
    def _loadApplicatives(self):
        for vhost in self.vhosts:
            directory = vhost['directory']
            if directory[0:2]=="./":
                directory = self.dirRoot + directory[2:]
            directory = os.path.dirname(directory)
            if directory[0:len(self.dirRoot+'app')]!=self.dirRoot+'app':
                raise Exception("Applicative must be in ./app directory")
            appName = directory[len(self.dirRoot+'app')+1:].replace("/", "-")
            directory = directory.replace("/", self.DS)
            if not appName in self.applicatives:
                self.applicatives[appName] = Instance(appName, directory)

    """
        Return list of applicatives availables by vhosts
        @returns list
    """
    def list(self) -> list:
        return list(self.applicatives.keys())

    """
        Resolve a http request with an applicative
        @param request  HttpRequest   http request
        @param response HttpResponse  http response
        @returns None
    """
    def resolve(self, request: HttpRequest, response: HttpResponse):
        directory = request.vhost["directory"]
        if directory[0:2]=="./":
            directory = self.dirRoot + directory[2:]
        directory = os.path.dirname(directory)
        appName = directory[len(self.dirRoot+'app')+1:].replace("/", "-")
        if directory[0:len(self.dirRoot+'app')]!=self.dirRoot+'app' or not appName in self.applicatives:
            response.code                       = 403
            response.body                       = "<doctype html><html><body><h1>403 - Forbidden</h1><hr></body></html>"
            response.headers['cacheControl']    = 'no-cache, no-store, max-age=0, must-revalidate'
            response.headers['contentType']     = 'text/html; chatset: utf-8'
            response.headers['connection']      = 'close'
            response.send()
        else:
            self.applicatives[appName].resolve(request, response)
