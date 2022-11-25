#!/usr/bin/env python3

from nano.config                       import Config
from nano.server.socketwrapper         import SocketWrapper
from nano.server.httprequest           import HttpRequest
from nano.server.httpresponse          import HttpResponse
from nano.server.filebuffer            import FileBuffer

import os
import re
import hashlib
import base64
import time
import datetime

"""
    Class for manage http protocol (including websocket)
"""
class HttpProtocol():

    UPLOAD_ERR_OK           = 0
    UPLOAD_ERR_INI_SIZE     = 1
    UPLOAD_ERR_FORM_SIZE    = 2
    UPLOAD_ERR_PARTIAL      = 3
    UPLOAD_ERR_NO_FILE      = 4
    UPLOAD_ERR_NO_TMP_DIR   = 6
    UPLOAD_ERR_CANT_WRITE   = 7
    UPLOAD_ERR_EXTENSION    = 8

    """
        Constructor
        @params  dirRoot    str       Server directory
        @params  config     Config    Server config
        @params  servername str       name returned by http server
        @returns None
    """
    def __init__(self, dirRoot: str, config: Config):
        self.vhosts             = config.get("vhost", [])
        self.SERVER             = config.get("serverName", "Server")
        self.DIR_ROOT           = dirRoot
        self.DS                 = os.path.sep
        self.METHODS            = config.get("http.methods", ["head", "get", "post", "put", "trace", "options", "trace", "connect"])
        self.VERSIONS           = config.get("http.versions", ["1.0", "1.1"])
        self.MAX_HEADER_SIZE    = config.get("http.maxheaderSize", 4096)
        self.MAX_REQUEST_SIZE   = config.get("http.maxRequestSize", 8388608)
        self.CODES              = config.get("http.codes", {"503":"Service Unavailable"})
        self.MIME_DEFAULT       = config.get("mimes.default", "application/octet-stream")
        self.MIMES              = config.get("mimes.byExtensions", {})
        self.BANDWIDTH_CHUNKSIZE= config.get("http.bandWidth.chunkSize", 256000)
        self.BANDWIDTH_DELAY    = config.get("http.bandWidth.delay", 500)
        self._socketCache       = {}

    """
        Parse data from socket
        @params  socket     SocketWrapper   Socket receiving data
        @params  port       int             Socket port
        @params  ssl        bool            If socket is over ssl
        @params  data       bytes           Data received
        @returns (HttpRequest, HttpResponse)
    """
    def parse(self, socket: SocketWrapper, port: int, ssl:bool, data: bytes) -> (HttpRequest, HttpResponse):

        proto = self.identifyProtocol(data)
        if proto=='http':
            return self.httpParse(socket, port, ssl, data)
        if proto=='websocket':
            return self.websocketParse(socket, port, ssl, data)
        # else prococol not recognozed
        socket.close()

    """
        Identify protocol from received data
        @params  data       bytes           Data received
        @returns protocol   str             Protocol name (expect http or websocket)
    """
    def identifyProtocol(self, data) -> str:

        # Look first line for identify protocol
        if data[0]==129 or data[0]==136:
            return 'websocket'

        line = data
        pos = data.find(13) # \n
        if pos >= 0:
            line = data[0:pos]
        line = line.decode('utf-8')

        find = re.search('^[A-Z]+\\s[^\\s]+\\sHTTP\\/[0-9]+\\.[0-9]+[\\r\\n]*', line, flags=re.IGNORECASE)
        if find != None:
            return 'http'

        return None

    """
        Parse http request
        @params  socket     SocketWrapper   Socket receiving data
        @params  port       int             Socket port
        @params  ssl        bool            If socket is over ssl
        @params  data       bytes           Data received
        @returns (HttpRequest, HttpResponse)
    """
    def httpParse(self, socket: SocketWrapper, port: int, ssl:bool, data: bytes) -> (HttpRequest, HttpResponse):

        data = data.decode('utf-8')

        request = HttpRequest()
        request.ssl = ssl
        request.headers["localHost"], request.headers["localPort"] = socket._local
        request.headers["remoteHost"], request.headers["remotePort"] = socket._remote

        # Check http structure
        #matches = data.match(/^([a-zA-Z]+)\s([ -~]+)\sHTTP\/([0-9]+\.[0-9]+)\r\n/i);
        output = re.search('(?s)^([a-zA-Z]+)\s([ -~]+)\sHTTP\/([0-9]+\.[0-9]+)\r\n', data, flags=re.IGNORECASE)
        if output is not None:
            output                          = output.group(0)
            buffer                          = output.split(" ")
            request.method                  = buffer[0].lower()
            request.headers["queryString"]  = buffer[1]
            protocol                        = buffer[2].split("/")
            request.protocol                = protocol[0].lower()
            request.scheme                  = request.protocol
            request.version                 = protocol[1][:-2].lower()

        # Chech http protocol version
        if not request.version in self.VERSIONS:
            socket.end(self._respondHttpCode(request.version, 505))
            return None, None

        # Uri length
        if len(request.headers["queryString"])>2000:
            socket.end(self._respondHttpCode(request.version, 414))
            return None, None

        # Chech http method
        if request.method not in self.METHODS:
            socket.end(self._respondHttpCode(request.version, 405))
            return None, None

        # Parse headers
        try:
            pos = data.index("\r\n\r\n")
        except ValueError as e:
            pos = -1
        headers = None
        if pos>0:
            headers = data[:pos]
            if pos<len(data)-4:
                request.body = data[pos+4:]
        else:
            headers = data
        headers = headers.split("\r\n")
        headers = headers[1:]
        for header in headers:
            if len(header)>self.MAX_HEADER_SIZE:
                socket.end(self._respondHttpCode(request.version, 431))
                return None, None
            output = re.search('^([a-zA-Z\-]+):\s{0,1}([ -~]+)$', header, flags=re.IGNORECASE)
            if output is not None:
                buffer = output.group(0)
                request.headers[self._httpname2camelcase(output.group(1))] = output.group(2)

        # Cookies
        if "Cookie" in request.headers:
            for cookie in request.headers["Cookie"]:
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
                request.cookies[name] = value

        # Clean header
        if "host" in request.headers:
            try:
                pos = request.headers["host"].index(':')
            except ValueError as e:
                pos = -1
            if pos>0:
                request.headers["host"] = request.headers["host"][0:pos]
            request.headers["host"] = request.headers["host"].lstrip("\/")
        if request.headers["queryString"]=="":
            request.headers["queryString"] = "/"

        # Vhost resolving
        request.vhost = None
        if "host" in request.headers:
            host = request.headers["host"]
            for vhost in self.vhosts:
                if vhost["port"]==port:
                    for hostrule in vhost["hosts"]:
                        pattern = "^"+hostrule+"$"
                        output = re.search(pattern, host, flags=re.IGNORECASE)
                        if output != None:
                            request.vhost = vhost
                            break
                    if request.vhost != None:
                        break

        # Socket cache
        key = str(hash(socket))
        self._socketCache[key] = {
            "protocolVersion"   : request.version,
            "headers"           : request.headers.copy(),
            "vhost"             : request.vhost
        }
        socket.on("close" , lambda args: self._socketCache.pop(key, None))

        # DIR_ROOT
        if request.vhost != None:
            dirRoot = request.vhost["directory"]
            if dirRoot[0:2]=="./":
                dirRoot = self.DIR_ROOT + dirRoot[2:]
            request.vhost["directory"] = dirRoot.replace("/", self.DS).rstrip(self.DS)+self.DS
            if "ssl" in request.vhost and request.vhost["ssl"] != None:
                request.scheme += "s"
        else:
            socket.close()
            return None, None

        # Acces control origin
        request.headers["accessControlAllowOrigin"] = request.headers["host"]
        request.headers["accessControlAllowMethod"] = "OPTIONS"

        # Websocket connexion upgrade
        if "secWebsocketVersion" in request.headers:
            if request.headers['secWebsocketVersion']!='13':
                # Websocket version not implemented
                socket.end(self._respondHttpCode(request.version, 501))
                return None, None

            key         = str(request.headers['secWebsocketKey'])+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
            digest      = hashlib.sha1(bytes(key, encoding='utf8')).digest()
            handshake   = base64.b64encode(digest).decode('ascii')
            scode       = str(101)
            buffer      = [
                'HTTP/'+(request.version)+' '+scode+' '+self.CODES[scode]+'\r\n',
                'Date: '+self._httpgmtdate()+'\r\n',
                'Server: '+self.SERVER+'\r\n',
                'Upgrade: websocket\r\n',
                'Sec-WebSocket-Accept: '+str(handshake)+'\r\n'
            ]
            if "origin" in request.headers:
                buffer.append('Sec-WebSocket-Origin :'+request.headers['origin']+"\r\n")

            buffer.extend([
                'Sec-WebSocket-Location: ws'+(ssl and 's' or '')+'://'+request.headers['host']+':'+str(port)+request.headers['queryString']+"\r\n",
                'Content-Length: 0\r\n',
                'Connection : Upgrade\r\n\r\n'
            ])

            socket.write(bytes("".join(buffer), encoding='utf-8'))

            # update socket behaviour
            socket.terminator = None

            return None, None

        # Extract get/post parameters
        DIR_UPLOAD = request.vhost["directory"] + "upload" + self.DS

        if request.method=="get":

            # Request size
            if len(data)>self.MAX_REQUEST_SIZE:
                socket.end(self._respondHttpCode(request.version, 413))
                return None, None

            # Parse GET
            try:
                pos = request.headers["queryString"].index('?')
            except ValueError as e:
                pos = -1
            if pos>=0 and pos<len(request.headers["queryString"])-1:
                buffer = request.headers["queryString"][pos+1:]
                buffer = buffer.split('&')
                for value in buffer:
                    try:
                        pos = value.index('=')
                    except ValueError as e:
                        pos = len(value)
                    if pos<len(value):
                        request.get[value[0:pos]] = value[pos+1:]
                    else:
                        request.get[value[0:pos]] = None

        elif request.method=="post":
            boundary = None
            if "contentType" in request.headers:
                output = re.search('(?s)\sboundary=([\-0-9]+)$', data, flags=re.IGNORECASE)
                if output is not None:
                    if "contentLength" not in request.headers:
                        socket.end(self._respondHttpCode(request.version, 411))
                        return None, None
                    boundary = output.group(1)

            output = request.body.search("(?s)^(\-+[0-9]+)\r\n", data, flags=re.IGNORECASE)
            if output is not None:
                try:
                    pos = output.group(1).index(boundary)
                except ValueError as e:
                    pos = -1
                if pos<0:
                    socket.end(self._respondHttpCode(request.version, 400))
                    return None, None                        
                maxSizeFile = None
                files       = []
                file        = None
                buffer      = request.body.split(output.group(1))

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

                    output = request.body.search("(?s);\sname=\"([ -:<-~]+)\"$", data, flags=re.IGNORECASE)
                    if output is not None:
                        # POST parmaeter
                        if output.group(1)=='MAX_FILE_SIZE':
                            maxSizeFile = int(body)
                        else:
                            request.post[output.group(1)] = body
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
                    request.files[file.name] = {
                        "filename"    : file["filename"],
                        "mime"        : file["mime"],
                        "tmpPath"     : file["tmpPath"],
                        "status"      : file["status"]
                    }
            else:
                # Request size
                if len(data)>self.MAX_REQUEST_SIZE:
                    socket.end(self._respondHttpCode(request.version, 413))
                    return None                        
                buffer = request.body.split('&')
                for value in buffer:
                    try:
                        pos = value.index('=')
                    except ValueError as e:
                        pos = -1
                    request.post[value[0, pos]] = value[pos+1:]

        else:
            # Request size
            if len(data)>self.MAX_REQUEST_SIZE:
                socket.end(self._respondHttpCode(request.version, 413))
                return None

        response            = HttpResponse()
        response.code       = 200
        response.protocol   = request.protocol
        response.ssl        = request.ssl
        response.version    = request.version
        response.headers    = {
            "server": self.SERVER,
            "date"  : self._httpgmtdate(),
        }

        # Asset mamagement
        assetPath   = dirRoot + "public" + self.DS
        filename    = request.headers["queryString"]
        try:
            pos = filename.index('?')
        except ValueError as e:
            pos = -1
        if pos>0:
            filename = filename[0:pos]
        try:
            pos = filename.index('#')
        except ValueError as e:
            pos = -1
        if pos>0:
            filename = filename[0:pos]

        # queryString match with a file
        path        = os.path.abspath(assetPath + filename.lstrip("/").replace("/", self.DS))
        if os.path.isfile(path):
            
            # Not alloed to leave app/public directory for assets
            if path[0:len(assetPath)]!=assetPath:
                socket.end(self._respondHttpCode(request.version, 400))
                return None, None

            # Extension
            ext = ""
            try:
                pos = path.rindex('.')
                ext = path[pos:]
            except ValueError as e:
                pos = -1  
            contentType = self.MIME_DEFAULT
            if ext in self.MIMES:
                contentType = self.MIMES[ext]
            response.headers["contentType"] = contentType
            response.headers["connection"] = "close" #"keep-alive"
            if "connection" in request.headers:
                response.headers["connection"] = request.headers["connection"]
            
            stat            = os.stat(path)
            byteStart       = 0
            byteFinish      = stat.st_size-1
            byteLength      = stat.st_size
            partialContent  = False            

            # 304 not modified
            mtime       = os.path.getmtime(path)
            if "ifModifiedSince" in request.headers:
                stime = self._httpfromgmttime(request.headers["ifModifiedSince"])
                if mtime<=stime:
                    response.headers["acceptRanges"] = 'bytes'
                    response.headers["contentLength"] = str(byteLength)
                    response.headers["cacheControl"] = 'public'
                    socket.end(self._httpFormatHeaders(request.version, 304, response.headers))
                    return None, None            

            # 206 partial content
            if "range" in request.headers:
                partialContent = True
                output = re.search('^bytes=([0-9]+)\-([0-9]*)$', request.headers["range"], flags=re.IGNORECASE)
                if output == None:
                    socket.end(self._respondHttpCode(request.version, 400))
                    return None, None
                byteStart       = int(output.group(1))
                if output.group(2)!="":
                    byteFinish = int(output.group(2))
                if byteFinish-byteStart>=stat.st_size:
                    byteFinish=stat.st_size-1-byteStart
                byteLength = byteFinish-byteStart+1

            # Prepare head
            if partialContent:
                code = 206
                response.headers["acceptRanges"] = 'bytes'
                response.headers["contentLength"]= str(byteLength)
                response.headers["contentRange"] = 'bytes '+str(byteStart)+'-'+str(byteFinish)+'/'+str(lstat.st_size),
                response.headers["cacheControl"] = 'no-cache'
                response.headers["pragma"]       = 'no-cache'
            else:
                code = 200
                #lastModified      : mtime.toGMTString(),
                response.headers["lastModified"] = self._httpgmtformat(mtime)
                response.headers["acceptRanges"] = "bytes"
                response.headers["contentLength"] = str(byteLength)

            socket.setkeepalive(True)

            # Send header
            socket.write(self._httpFormatHeaders(request.version, code, response.headers))
            
            # Send file as body
            fb = FileBuffer(socket, path, byteStart, byteLength, self.BANDWIDTH_CHUNKSIZE, self.BANDWIDTH_DELAY)
            fb.start()

            return None, None

        return request, response

    """
        Parse websocket request
        @params  socket     SocketWrapper   Socket receiving data
        @params  port       int             Socket port
        @params  ssl        bool            If socket is over ssl
        @params  data       bytes           Data received
        @returns (HttpRequest, HttpResponse)
    """
    def websocketParse(self, socket: SocketWrapper, port: int, ssl:bool, data: bytes) -> (HttpRequest, HttpResponse):

        socketCache = {
            "protocolVersion": "1.1",
            "headers": {
                "queryString": "/",
                "host": None,
            },
            "vhost": None
        }
        key = str(hash(socket))
        if key in self._socketCache:
            socketCache = self._socketCache[key]

        if data[0]==136:
            # Downgrade from websocket to http
            scode       = str(101)
            buffer      = [
                'HTTP/'+socketCache["protocolVersion"]+' '+scode+' '+self.CODES[scode]+'\r\n',
                'Date: '+self._httpgmtdate()+'\r\n',
                'Server: '+self.SERVER+'\r\n',
                'Upgrade: HTTP/1.1\r\n',
                'Content-Length: 0\r\n',
                'Connection : Upgrade\r\n\r\n'
            ]
            socket.write(bytes("".join(buffer), encoding='utf-8'))

            # update socket behaviour
            socket.terminator = b"\r\n\r\n"


        if data[0]!=129:
            # Invalid protocol
            socket.close()

        dataLength      = len(data)
        frameLength     = data[1] - 128
        body            = ''
        i               = 0

        if frameLength <= 125:
            #byte 0: The 0x81 is just an indicator that a message received
            #byte 1: the 0x8a is the length, substract 0x80 from it, 0x0A == 10
            #byte 2, 3, 4, 5: the 4 byte xor key to decrypt the payload
            #the rest: payload
            mask            = [data[2], data[3], data[4], data[5]]
            while 6 + i < dataLength:
                body += chr(data[6 + i] ^ mask[i % 4])
                i += 1
        elif frameLength == 126:
            #byte 0: The 0x81 is just an indicator that a message received
            #byte 1: will be 0xfe
            #byte 2, 3: the length of the payload as a uint16 number
            #byte 4, 5, 6, 7: the 4 byte xor key to decrypt the payload
            #the rest: payload            
            length          = (data[2]<<8 | data[3])
            mask            = [data[4], data[5], data[6], data[7]]
            while i < length:
                body += chr(data[8 + i] ^ mask[i % 4])
                i += 1
        elif frameLength == 127:
            #byte 0: The 0x81 is just an indicator that a message received
            #byte 1: will be 0xfe
            #byte 2, 3, 4, 5, 6, 7, 8, 9: the length of the payload as a uint16 number
            #byte 10, 11, 12, 13: the 4 byte xor key to decrypt the payload
            #the rest: payload            
            length          = data[2]>>56 | data[3]>>48 | data[4]>>40 | data[5]>>32 | data[6]>>24 | data[7]>>16 | data[8]>>8 | data[9]
            mask            = [data[10], data[11], data[12], data[13]]
            while i < length:
                body += chr(data[14 + i] ^ mask[i % 4])
                i += 1
        else:
            # Invalid protocol
            socket.close()


        request             = HttpRequest()
        request.ssl         = ssl
        request.protocol    = "websocket"
        request.scheme      = "ws"
        request.version     = "13"
        request.method      = "get"
        if ssl:
            request.scheme += "s"

        request.headers     = socketCache["headers"].copy()
        request.vhost       = socketCache["vhost"]

        request.body        = body

        response            = HttpResponse()
        response.code       = 200
        response.protocol   = request.protocol
        response.ssl        = request.ssl
        response.version    = request.version
        response.headers    = {
            "server"        : self.SERVER,
            "date"          : self._httpgmtdate(),
            "connexion"     : "keep-alive"
        }

        return request, response

    """
        Pack HttpResponse to raw http procotol bytearray
        @params  response   HttpResponse    Formatted http response
        @returns raw        bytes           Raw protocol bytearray
    """
    def pack(self, response: HttpResponse) -> bytes:

        if response.protocol == "http":
            return self.httpPack(response)
        if response.protocol=='websocket':
            return self.websocketPack(response)

        return b''

    """
        Pack HttpResponse to http procotol bytearray
        @params  response   HttpResponse    Formatted http response
        @returns raw        bytes           Raw protocol bytearray
    """
    def httpPack(self, response: HttpResponse) -> bytes:
        body = response.body.encode('utf-8')

        if not "contentLength" in response.headers:
            response.headers["contentLength"] = str(len(body))
        if not "connexion" in response.headers:
            response.headers["connexion"] = "close"

        head = self._httpFormatHeaders(response.version, response.code, response.headers)
        return b''.join([head,body])

    """
        Pack HttpResponse to websocket procotol bytearray
        @params  response   HttpResponse    Formatted http response
        @returns raw        bytes           Raw protocol bytearray
    """
    def websocketPack(self, response: HttpResponse) -> bytes:

        data = response.body
        length = len(data)

        # Crée l'entete websocket
        bytesFormatted = [129]
        if length <= 125:   
            bytesFormatted.append(length)               #1
        elif length >= 126 and length <= 65535:
            bytesFormatted.append(126)                  #1
            bytesFormatted.append((length  >> 8) & 255) #2
            bytesFormatted.append(length         & 255) #3
        else:
            bytesFormatted.append(127)                  #1
            bytesFormatted.append((length >> 56) & 255) #2
            bytesFormatted.append((length >> 48) & 255) #3
            bytesFormatted.append((length >> 40) & 255) #4
            bytesFormatted.append((length >> 32) & 255) #5
            bytesFormatted.append((length >> 24) & 255) #6
            bytesFormatted.append((length >> 16) & 255) #7
            bytesFormatted.append((length >>  8) & 255) #8
            bytesFormatted.append(length         & 255) #9

        for i in range(0, length):
            bytesFormatted.append(ord(data[i]))

        return bytearray(bytesFormatted)

    """
        To return on socket fast http code error
        @params  httpVersion    str     Version of HTTP
        @params  httpcode       int     Http code
        @returns raw            bytes   HTTP protocol bytearray
    """
    def _respondHttpCode(self, httpVersion: str, httpcode: int) -> bytes:
        scode = str(httpcode)
        buffer = [
            'HTTP/'+(httpVersion)+' '+scode+' '+self.CODES[scode]+'\r\n',
            'Date: '+self._httpgmtdate()+'\r\n',
            'Server: '+self.SERVER+'\r\n',
            'Cache-Control: no-cache, no-store, max-age=0, must-revalidate\r\n',
            'Content-Type: text/html; chatset: utf-8\r\n',
            'Content-Length: '+str(43+len(self.CODES[scode]))+'\r\n',
            'Connection: close\r\n',
            '\r\n',
            '<html><body><h1>'+scode+' '+self.CODES[scode]+'</h1><hr></body></html>',
        ]
        return bytes("".join(buffer), encoding='ascii')

    """
        Formater name to camelcase
        @params  name           str     From name
        @returns formatted      str     Formatted name
    """
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

    """
        Format camelcase http headers raw http protocol bytearray
        @params  protocolVersion    str     Version of http protocol
        @params  httpCode           str     Http code
        @params  headers            dict    Http headers
        @returns raw                bytes   http protocol bytearray
    """
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

    """
        Format one camelcase http headers to http protocol format
        @params  name           str     header name
        @params  name           dict    header value
        @returns raw            str     formatted
    """
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

    """
        GMT time for http
        @returns gmttime str
    """
    def _httpfromgmttime(self, gmttime: time) -> str:
        return datetime.datetime.timestamp(datetime.datetime.strptime(gmttime[5:-4], '%d %b %Y %H:%M:%S'))

    """
        GMT time format for http
        @param   timestamp int  Timestamp
        @returns gmttime   str
    """
    def _httpgmtformat(self, timestamp: int) -> str:
        now = datetime.datetime.fromtimestamp(timestamp)
        day = now.strftime("%A")[0:3]
        return day+', '+now.strftime("%d %b %Y %H:%M:%S")+' GMT'

    """
        GMT date for http
        @returns gmttime str
    """
    def _httpgmtdate(self) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        day = now.strftime("%A")[0:3]
        return day+', '+now.strftime("%d %b %Y %H:%M:%S")+' GMT'
