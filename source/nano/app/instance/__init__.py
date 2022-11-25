#!/usr/bin/env python3

from nano.config                import Config
from nano.server.httprequest    import HttpRequest
from nano.server.httpresponse   import HttpResponse
from nano.app.view              import View
from nano.app.error             import Error
from nano.app.log               import Log
from nano.app.lang              import Lang

import os
import re
import sys
import importlib

"""
    Class for manage one applicative
"""
class Instance():

    """
        Constructor: Prepare an applicatif from it's directory
        @param   appName           str  Name of app
        @param   appDirectoryPath  str  Directory of app
        @returns None
    """
    def __init__(self, appName: str, appDirectory: str):
        self.DS             = os.path.sep
        self.name           = appName
        self.directory      = appDirectory.rstrip("\\/")+self.DS
        self.Config         = Config(self.directory+"config")
        self.Log            = Log(self.directory+"log")
        self.Lang           = Lang(self.directory+"lang")
        self.Controllers    = {}
        self.Models         = {}
        self.Routes         = {}

        self._prepareprojectfiles()
        self.reloadModules()

    """
        Force reload applicative module
        @returns None
    """
    def reloadModules(self):

        self.Controllers    = {}
        self.Models         = {}
        self.Routes         = {}
        for controller in self._loadControllers():
            self.Routes[controller["route"]]                = controller["controllerName"]
            self.Controllers[controller["controllerName"]]  = controller["instance"]

        for model in self._loadModels():
            self.Models[model["modelName"]]                 = model["instance"]

    """
        Process a request to a response
        @param   request  HttpRequest   HTTP or Websocket Request (given)
        @param   response HttpResponse  HTTP or Websocket Response (to fill)
        @returns None
    """
    def resolve(self, request: HttpRequest, response: HttpResponse):

        developperMode = self.Config.get("global.developperMode", False)

        try:

            self.Config.update()
            self.Lang.updateFromRequest(request)
            self.Log.access(request)

            # Developper mode prevent app module caching
            if developperMode:
                self.reloadModules()

            # Routing
            (route, args) = self._routing(request)
            if route==None:
                self._responseError(404, 'Not found', request, response)
                return

            # Select controller and method
            segments= route.split('/')
            method  = segments.pop()
            route   = "/".join(segments)
            if not route in self.Routes:
                # Route has not valid controller
                self._responseError(410, 'Gone', request, response)
                return

            # Call it under error watcher
            try:

                def runController():

                    caller = getattr(self.Controllers[self.Routes[route]], method) # Get controller instance from route

                    if request.protocol=='http':
                        
                        # Prepare args from uri
                        argslength = (caller.__code__.co_argcount)-1  # expect "self"
                        while(len(args)<argslength):
                            args.append(None)

                        view = caller(*args)                          # Call it and return view

                        # Check controller return view
                        if not isinstance(view, View):
                            raise Exception("Controller \""+route+"\" return invalid View")

                        # map and return
                        (response.code, response.headers, response.body) = (view.code, view.headers, view.body)
                        response.send()

                    if request.protocol=='websocket':
                        
                        # Prepare args from uri
                        argslength = (caller.__code__.co_argcount)-2 # expect "self", "sender"
                        while(len(args)<argslength):
                            args.append(None)

                        def sender(message: str):
                            response.body = message
                            response.send()
                        view = caller(sender, *args)                          # Call it with a sender

                errorManager = Error()
                def onerror(args):
                    response.code                       = 503
                    if developperMode:
                        response.body                   = errorManager.wrap(request.protocol, args["exception"])
                        response.headers['cacheControl']= 'no-cache, no-store, max-age=0, must-revalidate'
                        response.headers['contentType'] = 'text/html; chatset: utf-8'
                        response.send()
                    else:
                        self._responseError(503, 'Service unavailable', request, response)
                    self.Log.error(args["exception"])
                    return

                errorManager.on("error", onerror)
                errorManager.watch(runController)

            # Double safety if error module has bug
            except Exception as e:
                self.Log.error(Exception("Instance resolve error (protocol: \""+request.protocol+"\", route: \""+route+"\"): "+str(e)).with_traceback(e.__traceback__))
                self._responseError(503, 'Service unavailable', request, response)
                return

        except Exception as e:
            self.Log.error(Exception("Instance resolve error (protocol: \""+request.protocol+"\"): "+str(e)).with_traceback(e.__traceback__))
            self._responseError(503, 'Service unavailable', request, response)
            return

    """
        If project if new (directory nort exists), create and initialize it
        @returns None
    """
    def _prepareprojectfiles(self):

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory, 0o774)

            todos = [
                { "action": "dir" , "target": "cache"                   , "mode": 0o774 },
                { "action": "dir" , "target": "config"                  , "mode": 0o774 },
                { "action": "dir" , "target": "controller"              , "mode": 0o775 },
                { "action": "dir" , "target": "lang"                    , "mode": 0o774 },
                { "action": "dir" , "target": "log"                     , "mode": 0o774 },
                { "action": "dir" , "target": "model"                   , "mode": 0o775 },
                { "action": "dir" , "target": "public"                  , "mode": 0o774 },
                { "action": "dir" , "target": "upload"                  , "mode": 0o774 },
                { "action": "file", "target": "config/global.json"      , "mode": 0o664 , "content": "{\n\t\"developperMode\": true\n}"},
                { "action": "file", "target": "config/databases.json"   , "mode": 0o664 , "content": "{}" },
                { "action": "file", "target": "config/routes.json"      , "mode": 0o664 , "content": "{\n\t\"http\": {},\n\t\"websocket\": {}\n}"}
            ]
            for todo in todos:
                if todo["action"]=="dir":
                    if not os.path.isdir(self.directory+todo["target"]):
                        os.mkdir(self.directory+todo["target"], todo["mode"])

                if todo["action"]=="file":
                    if not os.path.isfile(self.directory+todo["target"]):
                        f = open(self.directory+todo["target"], 'w')
                        f.write(todo["content"])
                        f.close()
                        os.chmod(self.directory+todo["target"], todo["mode"])

    """
        List files in directory (recursive)
        @param   path str  Directory path
        @returns None
    """
    def _listfiles(self, path: str) -> list:
        files = []
        list = os.listdir(path)
        for item in list:
            if os.path.isfile(path+item):
                files.append(path+item)
            if item != "__pycache__" and os.path.isdir(path+item):
                files += self._listfiles(path+item+self.DS)
        return files

    """
        UcFirst + CamelCase
        @param   snakecase str 
        @returns camelcase str
    """
    def _ucCamelCase(self, snakecase: str) -> str:
        if len(snakecase) == 0:
            return ""
        camelCase = ""
        upper = True
        for i in range(0, len(snakecase)):
            if snakecase[i] in "_./":
                upper = True
            else:

                if upper:
                    camelCase += snakecase[i].upper()
                    upper = False
                else:
                    camelCase += snakecase[i].lower()
        return camelCase

    """
        Load applicative controller modules
        @returns None
    """
    def _loadControllers(self):
                
        prefix = 'app.'+self.name+'.controller'
        loaded = []

        # Check if project controllers are in sys.modules
        for key in sys.modules.keys():
            if len(key)>len(prefix) and key[0:len(prefix)]==prefix:
                loaded.append(key)
        controllers = []

        # Get modules files list
        controllerPath = self.directory+"controller"+self.DS
        buffer = self._listfiles(controllerPath)
        files  = []

        for file in buffer:
            # Script only
            if len(file)>=3 and file[-3:]==".py":
                # ignore test.py which can break routing behaviour
                if file != "test.py":
                    # Ignore test files
                    if len(file)<8 or file[-8:]!="_test.py":
                        files.append(file)

        # Identify namespace and controllername
        for file in files:
            rpath = file[len(controllerPath):]
            try:
                pos = rpath.rindex(".")
                rpath = rpath[0:pos]
            except:
                pos = -1
            namespace = "app."+self.name+".controller."+rpath.replace(self.DS, '.')
            controllerName = 'Controller'+self._ucCamelCase(rpath)

            # Import module
            module = __import__(namespace, fromlist=[controllerName])
            if namespace in loaded:
                importlib.reload(module)
            controllerClass = getattr(module, controllerName)
            controllers.append({
                "namespace": namespace,
                "route": rpath,
                "controllerName": controllerName,
                "module": module,
                "controllerClass": controllerClass,
                "instance": controllerClass(self),
            })
        
        return controllers

    """
        Load applicative modle modules
        @returns None
    """
    def _loadModels(self) -> list:
        
        prefix = 'app.'+self.name+'.model'
        loaded = []

        # Check if project controllers are in sys.modules
        for key in sys.modules.keys():
            if len(key)>len(prefix) and key[0:len(prefix)]==prefix:
                loaded.append(key)
        models = []

        # Get modules files list
        modelPath = self.directory+"model"+self.DS
        buffer = self._listfiles(modelPath)
        files  = []

        for file in buffer:
            # Script only
            if len(file)>=3 and file[-3:]==".py":
                # ignore test.py which can break routing behaviour
                if file != "test.py":
                    # Ignore test files
                    if len(file)<8 or file[-8:]!="_test.py":
                        files.append(file)

        # Identify namespace and controllername
        for file in files:
            rpath = file[len(modelPath):]
            try:
                pos = rpath.rindex(".")
                rpath = rpath[0:pos]
            except:
                pos = -1
            namespace = "app."+self.name+".model."+rpath.replace(self.DS, '.')
            modelName = 'Model'+self._ucCamelCase(rpath)

            # Import module
            module = __import__(namespace, fromlist=[modelName])
            if namespace in loaded:
                importlib.reload(module)            
            modelClass = getattr(module, modelName)
            models.append({
                "namespace": namespace,
                "route": rpath,
                "modelName": modelName,
                "module": module,
                "modelClass": modelClass,
                "instance": modelClass(self),
            })

        return models

    """
        Route an URI to a controller
        @param   request  HttpRequest   HTTP or Websocket Request
        @returns None
    """
    def _routing(self, request):

        # Routing
        routes = self.Config.get("routes."+request.protocol, {})
        qstring = request.headers["queryString"]
        try:
            pos = qstring.index('?')
            qstring = qstring[0:pos]
        except ValueError as e:
            pos = -1

        route = None
        args = []
        for aroute in routes:
            output = re.search('^'+aroute+'$', qstring, flags=re.IGNORECASE)
            if output is not None:
                route = routes[aroute]
                args = output.groups()
                break
        if route==None:
            if '__404__' in routes:
                route = routes['__404__']
        argl = []
        for v in args:
            argl.append(v)
        return (route, argl)

    """
        Generate an Http response error
        @param   httpCode  int          HTTP code
        @param   httpLabel label        HTTP status label
        @param   request   HttpRequest  HTTP or Websocket Request
        @param   response  HttpResponse HTTP or Websocket Response
        @returns None
    """
    def _responseError(self, httpCode: int, httpLabel: str, request: HttpRequest, response: HttpResponse):
        response.code                       = httpCode
        if request.protocol=='http':
            response.body                   = "<doctype html><html><body><h1>"+str(httpCode)+" - "+httpLabel+"</h1><hr></body></html>"
            response.headers['cacheControl']= 'no-cache, no-store, max-age=0, must-revalidate'
            response.headers['contentType'] = 'text/html; chatset: utf-8'
        if request.protocol=='websocket':
            response.body                   = "<"+str(httpCode)+">"
        response.headers['connection']  = 'close'
        response.send()
