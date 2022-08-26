
import socket
import ssl
import threading
import sys
import errno
import re
import time
import datetime
import os
import hashlib
import json
from collections.abc import Iterable
from collections.abc import Callable
from pathlib import Path

SERVER = "Nano 2.14"

class Config:

    def __init__(self, path: str):
        self.path = path
        try:
            fd = open(path ,mode='r')
            data = fd.read()
            fd.close()
            self.data = json.loads(data)
        except Exception as e:
            raise e

    def __del__(self):
        self.data = None

    def get(self, xpath: str, defaultValue: str) -> str:
        segments = xpath.split('.')
        buffer   = self.data
        for segment in segments:
            if segment in buffer:
                buffer = buffer[segment]
            else:
                return defaultValue
        return buffer

class Listener(threading.Thread):

    def __init__(self, server: socket, port: int, wrapper: Callable, _onconnect: Callable):
        threading.Thread.__init__(self)
        self._server = server
        self._port = port
        self._wrapper = wrapper
        self.__onconnect = _onconnect
        self.listening = True

    def __del__(self):
        self.listening = False

    def run(self):
        while self.listening:
            try:
                conn, address = self._server.accept()
                self.__onconnect(self._wrapper(conn), self._port, address)
            except ssl.SSLError as e:
                msg = str(e)
                try:
                    pos = msg.index("SSLV3_ALERT_CERTIFICATE_UNKNOWN")
                    #print('<'+e.__class__.__name__+"> "+str(e))
                except ValueError as e:
                    print('<'+e.__class__.__name__+"> "+str(e))
                    self.listening = False
                    sys.exit(1)
            except Exception as e:
                print('<'+e.__class__.__name__+"> "+str(e))
                self.listening = False
                sys.exit(1)
        sys.exit(0)

class Conn(threading.Thread):

    def __init__(self, conn: socket, port: int, remotehost: str, remoteport: int, ondata: Callable):

        threading.Thread.__init__(self)
        self._conn = conn
        self._port = port
        self._remotehost = remotehost
        self._remoteport = remoteport
        self._ondata = ondata
        self._buffer = ""
        self.closed = False

    def __del__(self):
        self.closed = True

    def run(self):
        self._conn.setblocking(0)
        while not self.closed:
            if self._conn.fileno()<0:
                break
            try:
                data = self._conn.recv(2048)
                self._buffer = self._buffer + data.decode("utf-8")
                if self._buffer.endswith("\r\n\r\n"):
                    self._ondata(self, self._port, self._buffer, self._remotehost, self._remoteport)
                    self._buffer = ""
            except BlockingIOError:
                # No data
                continue
            except ssl.SSLWantReadError:
                # No data
                continue
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    continue
                else:
                    self._conn.shutdown(2)
                    print('<'+e.__class__.__name__+"> "+str(e))
                    break

        self.close()
        sys.exit(0)

    def setkeepalive(self, value):
        if value:
            self._conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        else:
            self._conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 0)

    def write(self, data):
        if not self.closed:
            self._conn.send(data)

    def close(self):
        self.closed = True
        self._conn.close()

class FileBuffer(threading.Thread):

    def __init__(self, conn: socket, path: str, byteStart: int, byteLength: int, bandWidthChunkSize: int, bandWidthDelay: int):
        threading.Thread.__init__(self)
        self._conn       = conn
        self._path       = path
        self._byteStart  = byteStart
        self._byteLength = byteLength
        self._chunkSize  = bandWidthChunkSize
        self._delay      = bandWidthDelay

    def __del__(self):
        self._conn.closed = True

    def run(self):
        eof         = False
        fd          = open(self._path, "rb")
        if self._byteStart>0:
            fd.seek(self._byteStart)
        start       = 0
        length      = self._byteLength
        chunksize   = 0
        while not self._conn.closed and not eof:
            chunksize = self._chunkSize
            if start+chunksize>length:
                chunksize = length-start
                eof = True
            chunk = fd.read(chunksize) #bytes(fd.read(chunksize), encoding='ascii')
            self._conn.write(chunk)
            start += chunksize

            if not eof:
                time.sleep(self._delay/1000)
        
        if not self._conn.closed:
            self._conn.close()

        sys.exit(0)

class Applicative(threading.Thread):

    def __init__(self, conn: socket, request, process: Callable, send: Callable):
        threading.Thread.__init__(self)
        self._conn          = conn
        self._request       = request
        self._process       = process
        self._send          = send

    def run(self):
        response = {
            "code"      : 200,
            "charset"   : "utf-8",
            "headers"   : {
                "contentType": "text/html"
            },
            "body"      : ""
        }
        self._process(self._request, response, self.callback)

    def callback(self, response):
        self._send(self._conn, self._request, response)
        
class Server:

    UPLOAD_ERR_OK           = 0
    UPLOAD_ERR_INI_SIZE     = 1
    UPLOAD_ERR_FORM_SIZE    = 2
    UPLOAD_ERR_PARTIAL      = 3
    UPLOAD_ERR_NO_FILE      = 4
    UPLOAD_ERR_NO_TMP_DIR   = 6
    UPLOAD_ERR_CANT_WRITE   = 7
    UPLOAD_ERR_EXTENSION    = 8

    def __init__(self, dirRoot: str):
        self.DIR_ROOT           = dirRoot
        self._onrequest         = lambda request, response, send: send(response)
        self.DS                 = os.path.sep
        self.servers            = {}
        self.config             = Config(dirRoot+"config.json")
        self.METHODS            = self.config.get("http.methods", ["head", "get", "post", "put", "trace", "options", "trace", "connect"])
        self.VERSIONS           = self.config.get("http.versions", ["1.0", "1.1"])
        self.MAX_HEADER_SIZE    = self.config.get("http.maxheaderSize", 4096)
        self.MAX_REQUEST_SIZE   = self.config.get("http.maxRequestSize", 8388608)
        self.CODES              = self.config.get("http.codes", {"503":"Service Unavailable"})
        self.MIME_DEFAULT       = self.config.get("http.mimeDefault", "application/octet-stream")
        self.MIMES              = self.config.get("http.mimes", {})
        self.BANDWIDTH_CHUNKSIZE= self.config.get("http.bandWidth.chunkSize", 256000)
        self.BANDWIDTH_DELAY    = self.config.get("http.bandWidth.delay", 500)

        # Collect port usage
        tlsports = []
        sslports = []
        vhosts = self.config.get("vhosts", [])
        for vhost in vhosts:

            if "port" in vhost and not vhost["port"] in tlsports:
                if not "ssl" in vhost or vhost["ssl"]==None:
                    tlsports.append({"port": vhost["port"] })

            if "port" in vhost and not vhost["port"] in sslports:
                if "ssl" in vhost and vhost["ssl"]!=None:
                    sslports.append({"port": vhost["port"], "ssl": vhost["ssl"] })

        wrapper = lambda sock: sock
        for item in tlsports:
            self._listen(item["port"], wrapper)

        for item in sslports:
            cert = item["ssl"]["cert"]
            if cert[0:2]=="./":
                cert = self.DIR_ROOT + cert[2:]
            private = item["ssl"]["private"]
            if private[0:2]=="./":
                private = self.DIR_ROOT + private[2:]
            wrapper = lambda sock: ssl.wrap_socket(sock, server_side=True, certfile=cert, keyfile=private)
            self._listen(item["port"], wrapper)
    def __del__(self):
        self.close()
    def _listen(self, port: int, wrapper: Callable):
        if not port in self.servers:
            server = socket.socket()
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind(("0.0.0.0", port))
                server.listen(1)
                self.servers[port] = server
                print(f'Server is listening on the port {port}')
                listener = Listener(server, port, wrapper, self._onconnect)
                listener.start()
            except socket.error as e:
                self.servers[port].close()
                del self.servers[port]
                print('<'+e.__class__.__name__+"> "+str(e))
    def close(self):
        try:
            for port in self.servers:
                self.servers[port].close()
                del self.servers[port]
        except Exception as e:
            print('<'+e.__class__.__name__+"> "+str(e))

    def _onconnect(self, conn: socket, port: int, address: str):
        thread = Conn(conn, port, address[0], str(address[1]), self._ondata)
        thread.start()
    def _ondata(self, conn: socket, port: int, data: str, remotehost: str, remoteport: str):
        request = self._httpparse(conn, port, data, remotehost, remoteport)
        if request != None:
            if not self._httpassetmanager(conn, request):
                #Applicative
                self._appmanager(conn, request)
        return
    def onrequest(self, callback: Callable):
        self._onrequest = callback

    def _httpparse(self, conn: socket, port: int, data: str, remotehost: str, remoteport: str):

        request = {
            "protocol": None,
            "port"    : port,
            "remote"  : {
                "addr": remotehost,
                "port": remoteport
            },
            "method"  : None,
            "vhost"   : None,
            "version" : None,
            "headers" : {
                "host": None,
                "queryString" : None,
                "accessControlAllowOrigin": None,
                "accessControlAllowMethod": None,
            },
            "get"       : {},
            "post"      : {},
            "cookies" 	: {},
            "body"		: "", 
            "files"   	: {},
        }

        # Check http structure
        #matches = data.match(/^([a-zA-Z]+)\s([ -~]+)\sHTTP\/([0-9]+\.[0-9]+)\r\n/i);
        output = re.search('(?s)^([a-zA-Z]+)\s([ -~]+)\sHTTP\/([0-9]+\.[0-9]+)\r\n', data, flags=re.IGNORECASE)
        if output is not None:
            output = output.group(0)
            buffer = output.split(" ")
            request["method"] = buffer[0].lower()
            request["headers"]["queryString"] = buffer[1]
            protocol = buffer[2].split("/")
            request["protocol"] = protocol[0].lower()
            request["version"] = protocol[1][:-2].lower()

        # Chech http protocol version
        if not request["version"] in self.VERSIONS:
            conn.write(self._httpfastformat(request["version"], 505))
            conn.close()
            return None

        # Uri length
        if len(request["headers"]["queryString"])>2000:
            conn.write(self._httpfastformat(request["version"], 414))
            return None
        
        # Chech http method
        if request["method"] not in self.METHODS:
            conn.write(self._httpfastformat(request["version"], 405))
            return None
        
        # Parse headers
        try:
            pos = data.index("\r\n\r\n")
        except ValueError as e:
            pos = -1
        headers = None
        if pos>0:
            headers = data[:pos]
            if pos<len(data)-4:
                request["body"] = data[pos+4:]
        else:
            headers = data
        headers = headers.split("\r\n")
        headers = headers[1:]
        for header in headers:
            if len(header)>self.MAX_HEADER_SIZE:
                conn.write(self._httpfastformat(request["version"], 431))
                return None
            output = re.search('^([a-zA-Z\-]+):\s{0,1}([ -~]+)$', header, flags=re.IGNORECASE)
            if output is not None:
                buffer = output.group(0)
                request["headers"][self._httpname2camelcase(output.group(1))] = output.group(2)

        # Cookies
        if "Cookie" in request["headers"]:
            for cookie in request["headers"]["Cookie"]:
                try:
                    pos = cookie.index('=')
                except ValueError as e:
                    pos = -1
                name = None
                value = None
                if pos>0:
                    name = cookie[0, pos].lstrip(" ")
                    value= cookie[pos+1:]
                else:
                    name = cookie
                    value = ''
                request["cookies"][name] = value

        # Clean header
        if "host" in request['headers']:
            try:
                pos = request['headers']["host"].index(':')
            except ValueError as e:
                pos = -1
            if pos>0:
                request['headers']["host"] = request['headers']["host"][0:pos]
            request['headers']["host"] = request['headers']["host"].lstrip("\/")

        # Vhost resolving
        if "host" in request["headers"]:
            host = request["headers"]["host"]
            vhosts = self.config.get("vhosts", [])
            for vhost in vhosts:
                if vhost["port"]==port:
                    for hostrule in vhost["hosts"]:
                        pattern = "^"+hostrule+"$"
                        output = re.search(pattern, host, flags=re.IGNORECASE)
                        if output != None:
                            request["vhost"] = vhost
                            break
                    if request["vhost"] != None:
                        break

        # DIR_ROOT
        if "vhost" in request:
            dirRoot = request["vhost"]["directory"]
            if dirRoot[0:2]=="./":
                dirRoot = self.DIR_ROOT + dirRoot[2:]
            request["vhost"]["directory"] = dirRoot.replace("/", self.DS).rstrip(self.DS)+self.DS
            if "ssl" in request["vhost"] and request["vhost"]["ssl"] != None:
                request["protocol"] += "s"
        else:
            conn.close()
            return None

        # Acces control origin
        request["headers"]["accessControlAllowOrigin"] = request['headers']["host"]
        request["headers"]["accessControlAllowMethod"] = "OPTIONS"

        # Websocket not allowed
        if "secWebsocketVersion" in request["headers"]:
            conn.send(self._httpfastformat(request["version"], 400))
            return None

        # Extract get/post parameters
        DIR_UPLOAD = request["vhost"]["directory"] + "upload" + self.DS

        if request["method"]=="get":
            # Request size
            if len(data)>self.MAX_REQUEST_SIZE:
                conn.send(self._httpfastformat(request["version"], 413))
                return None
            # Parse GET
            try:
                pos = request['headers']["queryString"].index('?')
            except ValueError as e:
                pos = -1
            if pos>=0 and pos<len(request['headers']["queryString"])-1:
                buffer = request['headers']["queryString"][pos+1:]
                buffer = buffer.split('&')
                for value in buffer:
                    try:
                        pos = value.index('=')
                    except ValueError as e:
                        pos = len(value)
                    if pos<len(value):
                        request['get'][value[0:pos]] = value[pos+1:]
                    else:
                        request['get'][value[0:pos]] = None

        else:
            if request["method"]=="post":
                boundary = None
                if "contentType" in request["headers"]:
                    output = re.search('(?s)\sboundary=([\-0-9]+)$', data, flags=re.IGNORECASE)
                    if output is not None:
                        if "contentLength" not in request["headers"]:
                            conn.send(self._httpfastformat(request["version"], 411))
                            return None
                        boundary = output.group(1)

                output = request["body"].search("(?s)^(\-+[0-9]+)\r\n", data, flags=re.IGNORECASE)
                if output is not None:
                    try:
                        pos = output.group(1).index(boundary)
                    except ValueError as e:
                        pos = -1
                    if pos<0:
                        conn.send(self._httpfastformat(request["version"], 400))
                        return None                        
                    maxSizeFile = None
                    files       = []
                    file        = None
                    buffer      = request["body"].split(output.group(1))

                    for fileRaw in buffer:
                        try:
                            pos = fileRaw.index("\r\n\r\n")
                        except ValueError as e:
                            pos = -1                        
                        header  = None
                        file    = {}
                        body    = None
                        if pos>0:
                            header = fileRaw[0, pos]
                            body = fileRaw[pos+4:].rstrip("\r\n")
                            if body==None:
                                bod = ""
                        else:
                            header = fileRaw
                            body = ''

                        output = request["body"].search("(?s);\sname=\"([ -:<-~]+)\"$", data, flags=re.IGNORECASE)
                        if output is not None:
                            # POST parmaeter
                            if output.group(1)=='MAX_FILE_SIZE':
                                maxSizeFile = int(body)
                            else:
                                request["post"][output.group(1)] = body
                        else:
                            output = header.search(";\sname=\"([ -:<-~]+)\";\sfilename=\"([ -:<-~]+)\"\r\nContent\-Type:\s([ -:<-~]+)$", data, flags=re.IGNORECASE)
                            if output is not None:
                                # File
                                files.push({
                                    "name"    : output.group(1),
                                    "filename": output.group(2),
                                    "mime"    : output.group(3),
                                    "tmpPath" : None,
                                    "status"  : None,
                                    "data"    : body
                                })

                    for file in files:
                        size = len(file["data"])
                        if size>self.MAX_REQUEST_SIZE:
                            file["status"] = self.UPLOAD_ERR_INI_SIZE
                        else:
                            if maxSizeFile!=None and size>maxSizeFile:
                                file["status"] = self.UPLOAD_ERR_FORM_SIZE
                            else:
                                if size==0:
                                    file["status"] = self.UPLOAD_ERR_NO_FILE
                                else:
                                    if not os.path.isdir(DIR_UPLOAD):
                                        file["status"] = self.UPLOAD_ERR_NO_TMP_DIR
                                    else:
                                        try:
                                            # Write tmp file
                                            tmpFile = hashlib.md5(file.filename+':'+file.data).hexdigest()+'.tmp'
                                            fd = open(tmpFile, "w")
                                            fd.write(file.data)
                                            fd.close()
                                            file["tmpPath"] = tmpFile
                                            file["status"] = self.UPLOAD_OK
                                        except Exception as e:
                                            file["status"] = self.UPLOAD_ERR_CANT_WRITE
                        del file["data"]
                        request["files"][file.name] = {
                            "filename"    : file["filename"],
                            "mime"        : file["mime"],
                            "tmpPath"     : file["tmpPath"],
                            "status"      : file["status"]
                        }
                else:
                    # Request size
                    if len(data)>self.MAX_REQUEST_SIZE:
                        conn.write(self._httpfastformat(request["version"], 413))
                        return None                        
                    buffer = request["body"].split('&')
                    for value in buffer:
                        try:
                            pos = value.index('=')
                        except ValueError as e:
                            pos = -1
                        request["post"][value[0, pos]] = value[pos+1:]

            else:
                # Request size
                if len(data)>self.MAX_REQUEST_SIZE:
                    conn.write(self._httpfastformat(request["version"], 413))
                    return None


        return request
    def _httpfastformat(self, httpVersion: str, httpcode: int) -> bytes:
        scode = str(httpcode)
        buffer = [
            'HTTP/'+(httpVersion)+' '+scode+' '+self.CODES[scode]+'\r\n',
            'Date: '+self._httpgmtdate()+'\r\n',
            'Server: '+SERVER+'\r\n',
            'Cache-Control: no-cache, no-store, max-age=0, must-revalidate\r\n',
            'Content-Type: text/html; chatset: utf-8\r\n',
            'Content-Length: '+str(43+len(self.CODES[scode]))+'\r\n',
            'Connection: close\r\n',
            '\r\n',
            '<html><body><h1>'+scode+' '+self.CODES[scode]+'</h1><hr></body></html>',
        ]
        return bytes("".join(buffer), encoding='ascii')
    def _httpname2camelcase(self, name: str) -> str:
        camelCase   = ''
        i           = 0
        length      = len(name)
        char        = None
        upper       = False
        for i in range(0, length):
            char = name[i]
            if char=='-':
                upper = True
            else:
                if upper:
                    camelCase += char.upper()
                else:
                    camelCase += char.lower()
                upper = False
        return camelCase

    def _httpassetmanager(self, conn: socket, request):

        DIR_PUBLIC = request["vhost"]["directory"] + "public" + self.DS

        # Clean path
        path = request["headers"]["queryString"]
        try:
            pos = path.index('?')
        except ValueError as e:
            pos = -1
        lstat= None
        if pos>0:
            path = path[0:pos]
        try:
            pos = path.index('#')
        except ValueError as e:
            pos = -1            
        if pos>0:
            path = path[0:pos]
            
        path = DIR_PUBLIC + path.lstrip("/").replace("/", self.DS)

        # File exists ?
        if not os.path.isfile(path):
            return False

        # Prepare response format
        headers = {
            "server": SERVER,
            "date"  : self._httpgmtdate(),
        }

        ext = ""
        try:
            pos = path.rindex('.')
            ext = path[pos:]
        except ValueError as e:
            pos = -1  
        contentType = self.MIME_DEFAULT
        if ext in self.MIMES:
            contentType = self.MIMES[ext]
        headers["contentType"] = contentType
        headers["connection"] = "keep-alive"
        if "connection" in request["headers"]:
            headers["connection"] = request["headers"]["connection"]

        stat            = os.stat(path)
        byteStart       = 0
        byteFinish      = stat.st_size-1
        byteLength      = stat.st_size
        partialContent  = False

        # 304 not modified
        mtime       = os.path.getmtime(path)
        if "ifModifiedSince" in request["headers"]:
            stime = self._httpfromgmttime(request["headers"]["ifModifiedSince"])
            if mtime<=stime:
                headers["acceptRanges"] = 'bytes'
                headers["contentLength"] = str(byteLength)
                headers["cacheControl"] = 'public'
                conn.write(self._httpFormatHeaders(request["version"], 304, headers))
                return True

        # 206 partial content
        if "range" in request["headers"]:
            partialContent = True
            output = re.search('^bytes=([0-9]+)\-([0-9]*)$', request["headers"]["range"], flags=re.IGNORECASE)
            if output == None:
                conn.send(self._httpfastformat(request["version"], 400))
                return True
            byteStart       = int(output.group(1))
            if output.group(2)!="":
                byteFinish = int(output.group(2))
            if byteFinish-byteStart>=stat.st_size:
                byteFinish=stat.st_size-1-byteStart
            byteLength = byteFinish-byteStart+1

        # Prepare head
        if partialContent:
            code = 206
            headers["acceptRanges"] = 'bytes'
            headers["contentLength"] = str(byteLength)
            headers["contentRange"] = 'bytes '+str(byteStart)+'-'+str(byteFinish)+'/'+str(lstat.st_size),
            headers["cacheControl"] = 'no-cache'
            headers["pragma"] = 'no-cache'

        else:
            code = 200
            #lastModified      : mtime.toGMTString(),
            headers["lastModified"] = self._httpgmtformat(mtime)
            headers["acceptRanges"] = "bytes"
            headers["contentLength"] = str(byteLength)

        conn.setkeepalive(True)
        # Send header
        conn.write(self._httpFormatHeaders(request["version"], code, headers))
        # Send file as body
        fb = FileBuffer(conn, path, byteStart, byteLength, self.BANDWIDTH_CHUNKSIZE, self.BANDWIDTH_DELAY)
        fb.start()

        return True
    def _httpFormatHeaders(self, protocolVersion: str, httpCode: int, headers: dict) -> bytes:
        scode = str(httpCode)
        buffer = ['HTTP/' + protocolVersion + ' ' + scode + ' ' + self.CODES[scode] + "\r\n"]
        for name in headers:
            if isinstance(headers[name], str):
                buffer.append(self._httpFormatHeader(name, headers[name])+"\r\n")
            else:
                if isinstance(headers[name], Iterable):
                    for sub in headers[name]:
                        buffer.append(self._httpFormatHeader(name, sub)+"\r\n")
        buffer.append("\r\n")
        return bytes("".join(buffer), encoding='utf-8')
    def _httpFormatHeader(self, name: str, value: str) -> str:
        buffer  = ''
        char    = ''
        for i in range(0, len(name)):
            char = name[i]
            if i==0:
                buffer += char.upper()
            else:
                if char==char.upper():
                    buffer += '-'+char
                else:
                    buffer += char
        name = buffer
        return name + ': ' + value
    def _httpfromgmttime(self, gmttime: time) -> str:
        return datetime.datetime.timestamp(datetime.datetime.strptime(gmttime[5:-4], '%d %b %Y %H:%M:%S'))
    def _httpgmtformat(self, timestamp: int) -> str:
        now = datetime.datetime.fromtimestamp(timestamp)
        day = now.strftime("%A")[0:3]
        return day+', '+now.strftime("%d %b %Y %H:%M:%S")+' GMT'
    def _httpgmtdate(self) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        day = now.strftime("%A")[0:3]
        return day+', '+now.strftime("%d %b %Y %H:%M:%S")+' GMT'

    def _appmanager(self, conn: socket, request):
        apprun = Applicative(conn, request, self._onrequest, self._appresponse)
        apprun.start()
    def _appresponse(self, conn: socket, request, response):
        if not "encoding" in response:
            response["encoding"] = 'ascii'
        response["headers"]["date"] = self._httpgmtdate()
        response["headers"]["server"] = SERVER
        response["headers"]["contentLength"] = len(response["body"])
        if not "cacheControl" in response["headers"]:
            response["headers"]["cacheControl"] = "no-cache, no-store, max-age=0, must-revalidate"
        scode = str(response["code"])
        buffer = [
            'HTTP/'+(request["version"])+' '+scode+' '+self.CODES[scode]+'\r\n',
        ]
        for header in response["headers"]:
            buffer.append(self._httpcamelcase2name(header)+': '+str(response["headers"][header])+"\r\n")
        buffer.append("\r\n")
        buffer.append(response["body"])
        conn.write(bytes("".join(buffer), encoding=response["encoding"]))
    def _httpcamelcase2name(self, camel: str) -> str:
        name = ""
        length = len(camel)
        for i in range(0, length):
            char = camel[i]
            if i==0:
                name += char.upper()
            else:
                if char == char.upper():
                    name += '-'
                name += char
        return name

