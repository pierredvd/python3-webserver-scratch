import os
import json
import re
import threading
import sys
import psycopg2
import importlib
import datetime
from psycopg2.extras import RealDictCursor
from collections.abc import Callable
from collections.abc import Iterable

class Applicatives():

    def __init__(self, dirRoot: str):
        self.DS         = os.path.sep
        self._dirRoot   = dirRoot
        self._apps      = {}

    def run(self, request, response, send):

        # Applicative load and cache code
        path = request["vhost"]["directory"]
        base = self._dirRoot+"app"+self.DS
        if path[0:len(base)] != base:
            raise BaseException("App have to be in server \"app\" directory")
        project = path[len(base):].rstrip(self.DS)

        if not project in self._apps:
            self._apps[project] = Applicative(path, project)

        # Call applicative run
        self._apps[project].run(request, response, send)

    def list(self):
        path = self._dirRoot+'app'
        list = os.listdir(path)
        apps = []
        for item in list:
            if item != "__pycache__" and os.path.isdir(path+self.DS+item):
                apps.append(item)
        return apps

    def test(self, appName):
        if not appName in self.list():
            raise BaseException("app \""+appName+"\" not found")
        print("@TODO run test")

class Applicative():

    def __init__(self, path: str, project: str):
        self.DS             = os.path.sep
        self._prepareprojetfiles(path)
        self._path          = path
        self._project       = project
        self._reloadModules()
    def __del__(self):
        self.Model.close()

    def _prepareprojetfiles(self, path: str):

        # Force config.json file
        if not os.path.isfile(path+"config.json"):
            f = open(path+"config.json", 'w')
            f.write("{\t\"routes\": {\r\n\t\t\"__404__\"\t: \"404/index\",\r\n\t\t"/"\t\t: \"index/index\"\r\n\t},\r\n\t}\r\n}")
            f.close()

        # controller
        if not os.path.isdir(path+"controller"):
            os.mkdir(path+"controller", 0o666)
            f = open(path+"controller"+self.DS+"index.py", 'w')
            f.write("class ControllerIndex:\r\n\r\n\tdef __init__(self, Nano):\r\n\t\tself.Nano = Nano\r\n\r\n\tdef index(self):\r\n\t\treturn self.Nano.View.Json(200, {\"status\": \"Hello, world !\"}, {})")
            f.close()
            f = open(path+"controller"+self.DS+"404.py", 'w')
            f.write("class Controller404:\r\n\r\n\tdef __init__(self, Nano):\r\n\t\tself.Nano = Nano\r\n\r\n\tdef index(self):\r\n\t\treturn self.Nano.View.Json(404, {\"status\": \"Not found\"}, {})")
            f.close()

        # model
        if not os.path.isdir(path+"model"):
            os.mkdir(path+"model", 0o666)
            f.close()

        # log
        if not os.path.isdir(path+"log"):
            os.mkdir(path+"log", 0o666)

        # test
        if not os.path.isdir(path+"test"):
            os.mkdir(path+"test", 0o666)

        # cache
        if not os.path.isdir(path+"cache"):
            os.mkdir(path+"cache", 0o666)

        # lang
        if not os.path.isdir(path+"lang"):
            os.mkdir(path+"lang", 0o666)

        # public
        if not os.path.isdir(path+"public"):
            os.mkdir(path+"public", 0o666)
            f = open(path+"public"+self.DS+"index.htm", 'w')
            f.write("<DOCTYPE html />\r\n<html>\r\n\t<body><h1>Hello, world !</h1><hr></body>\r\n</html>")
            f.close()

        # public
        if not os.path.isdir(path+"upload"):
            os.mkdir(path+"upload", 0o660)
    def _listfiles(self, path: str) -> list:
        files = []
        list = os.listdir(path)
        for item in list:
            if os.path.isfile(path+item):
                files.append(path+item)
            if item != "__pycache__" and os.path.isdir(path+item):
                files += self._listfiles(path+item+self.DS)
        return files
    def _loadControllers(self, path: str) -> list:
        prefix = 'app.'+self._project+'.controller'
        loaded = []
        for key in sys.modules.keys():
            if len(key)>len(prefix) and key[0:len(prefix)]==prefix:
                loaded.append(key)
        controllers = []
        controllerPath = path+"controller"+self.DS
        list = self._listfiles(controllerPath)
        for item in list:
            rpath = item[len(controllerPath):]
            try:
                pos = rpath.rindex(".")
                rpath = rpath[0:pos]
            except:
                pos = -1
            namespace = "app."+self._project+".controller."+rpath.replace(self.DS, '.')
            controllerName = 'Controller'+rpath[0].upper()
            for i in range(1, len(rpath)):
                if rpath[i]!='/':
                    if rpath[i-1]=='/':
                        controllerName += rpath[i].upper()
                    else:
                        controllerName += rpath[i].lower()
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
    def _loadModels(self, path: str) -> list:
        prefix = 'app.'+self._project+'.model'
        loaded = []
        for key in sys.modules.keys():
            if len(key)>len(prefix) and key[0:len(prefix)]==prefix:
                loaded.append(key)
        models = []
        modelPath = path+"model"+self.DS
        list = self._listfiles(modelPath)
        for item in list:
            rpath = item[len(modelPath):]
            try:
                pos = rpath.rindex(".")
                rpath = rpath[0:pos]
            except:
                pos = -1
            namespace = "app."+self._project+".model."+rpath.replace(self.DS, '.')
            modelName = 'Model'+rpath[0].upper()
            for i in range(1, len(rpath)):
                if rpath[i]!='/':
                    if rpath[i-1]=='/':
                        modelName += rpath[i].upper()
                    else:
                        modelName += rpath[i].lower()
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
    def _reloadModules(self):

        self.Config         = Config(self._path+"config.json")
        self.Model          = Model(self.Config.get("databases", {}))
        self.View           = View()
        self._controllers   = self._loadControllers(self._path)
        self._routes        = {}
        self.Controllers    = {}
        self._models        = self._loadModels(self._path)
        self.Models         = {}

        for c in self._controllers:
            self._routes[c["route"]] = c["instance"]
            self.Controllers[c["controllerName"]] = c["instance"]

        for m in self._models:
            self.Models[m["modelName"]] = m["instance"]

    def run(self, request, response, send):

        try:

            # Developper mode prevent app module caching
            if self.Config.get("developperMode", False):
                self._reloadModules()

            # Routing
            (route, args) = self._routing(request)
            if route==None:
                send(self.e404(response, send))
                return

            # Select controller and method
            segments= route.split('/')
            method  = segments.pop()
            route   = "/".join(segments)
            if not route in self._routes:
                print("Route \""+route+"\" has no valid controller")
                send(self._e503(response))
                return

            # Call it
            try:
                caller = getattr(self._routes[route], method)
                argslength = (caller.__code__.co_argcount)-1
                while(len(args)<argslength):
                    args.append(None)
                view = caller(*args)
            except Exception as e:
                print(str(e))
                send(self._e503(response))
                return

            # Check controller return view
            if not isinstance(view, View):
                print("Controller \""+route+"\" return invalid View")
                self._e503(response, send)
                return

            # map and return
            (response["code"], response["headers"], response["body"]) = (view.code, view.headers, view.body)
            send(response)

        except Exception as e:
            print("<"+e.__class__.__name__+'> '+str(e))
            self._e503(response, send)

    def _routing(self, request):

        # Routing
        routes = self.Config.get("routes", {})
        qstring = request["headers"]["queryString"]
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
        list = []
        for v in args:
            list.append(v)

        return (route, list)
    def _e404(self, response):
        response["code"] = 404
        response["encoding"] = "utf-8"
        response["headers"]["contentLength"] = 52
        response["body"] =  '<html><body><h1>404 Not found</h1><hr></body></html>'
        return response
    def _e503(self, response):
        response["code"] = 503
        response["encoding"] = "utf-8"
        response["headers"]["contentLength"] = 62
        response["body"] =  '<html><body><h1>503 Service Unavailable</h1><hr></body></html>'
        return response

class Config:

    def __init__(self, path):
        self.path = path
        self._lastmtime = self.mtime()
        self.reload()

    def reload(self):
        try:
            fd = open(self.path ,mode='r')
            data = fd.read()
            fd.close()
            self.data = json.loads(data)
        except Exception as e:
            raise e

    def get(self, xpath, defaultValue):
        # Check if need reload
        if self.mtime() > self._lastmtime:
            self.reload()
        segments = xpath.split('.')
        buffer   = self.data
        for segment in segments:
            if segment in buffer:
                buffer = buffer[segment]
            else:
                return defaultValue
        return buffer

    def mtime(self):
        stat = os.stat(self.path)
        return stat.st_mtime

class Model:

    def __init__(self, connexions):
        self.connexions = connexions
        self._conn = {}

    def __del__(self):
        self.close()

    def query(self, connexion, sql):
        if not connexion in self.connexions:
            raise BaseException("Unknown connexion \""+connexion+"\"")

        if not connexion in self._conn:
            self._conn[connexion] = psycopg2.connect(
                host    = self.connexions[connexion]["host"],
                dbname  = self.connexions[connexion]["database"],
                user    = self.connexions[connexion]["user"],
                password= self.connexions[connexion]["password"],
                port    = self.connexions[connexion]["port"]
            )

        cursor = self._conn[connexion].cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        data = []
        datamap = {} 
        for record in records:
            data.append(dict(record))
        return data

    def close(self):
        for conn in self._conn:
            self._conn[conn].close()
        self._conn = {}    

class View:

    def __init__(self):
        self.code = 200
        self.body = ""
        self.headers = {}
    def _reset(self):
        self.code = 200
        self.body = ""
        self.headers = {}
    def _serializable(self, data):
        if isinstance(data, datetime.datetime):
            return int(datetime.datetime.timestamp(data))
        if isinstance(data, list):
            for i in range(len(data)):
                data[i] = self._serializable(data[i])
        if isinstance(data, dict):
            for key in data:
                data[key] = self._serializable(data[key])

        return data

    def Json(self, code, data, headers):
        self._reset()
        self.code = code
        self.body = json.dumps(self._serializable(data), sort_keys=True)
        for key in headers:
            self.headers[key] = headers[key]
        self.headers["contentType"] = "text/json; chatset: utf-8"
        self.headers["connection"] = "close"
        return self

    def Html(self, code, data, headers):
        self._reset()
        self.code = code
        self.body = data
        for key in headers:
            self.headers[key] = headers[key]
        self.headers["contentType"] = "text/html; chatset: utf-8"
        self.headers["connection"] = "keep-alive"
        return self

    def Redirect(self, url):
        self._reset()
        self.code = 302
        self.body = ""
        self.headers["location"] = url
        return self
