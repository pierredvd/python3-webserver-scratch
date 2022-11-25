#!/usr/bin/env python3

from nano.event                  import Event

from collections.abc import Callable
import os
import re
import sys
import traceback

"""
    Class for visual errors
"""
class Error():

    template = ""

    def __init__(self):
        self._event = Event()

    def _loadTemplate(self):
        if type(self).template == "":
            f = open(__file__,"r")
            lines = f.readlines()
            f.close()
            template = ""
            isTemplate = False
            for line in lines:
                line = line.rstrip("\r\n\t\n")
                if not isTemplate and line=='""" <template>':
                    isTemplate = True
                else:
                    if isTemplate:
                        if line=='"""':
                            break;  
                        template += line + "\r\n"
            type(self).template = template
        return type(self).template

    def watch(self, callback: Callable):
        try:
            callback()
        except Exception as e:
            self._event.fire("error", { "exception": e.with_traceback(sys.exc_info()[2]) })

    def on(self, eventName: str, callback: Callable):
        self._event.on(eventName, callback)

    def wrap(self, protocol: str, e: Exception) -> str:
        etype    = e.__class__.__name__
        emessage = str(e)
        traces   = (''.join(traceback.format_tb(e.__traceback__)))
        
        if protocol!='http':
            return "["+etype+"] "+emessage+"\r\n\r\n"+traces

        # HTTP Skinning
        traces = traces.split("\n")
        content = ""
        buffer  = []

        # parse and reverse backtrace
        for i in range(0, len(traces), 2):
            output = re.search('^[\s\t\r\n]*File\s\"([^"]+)\", line ([0-9]+), in ([^\r\n\t\s]+).*$', traces[i], flags=re.IGNORECASE)
            if output is not None:
                (path, line, lsb) = output.groups()
                buffer.insert(0, (path, line, lsb))

        # formatting        
        for i in range(0, len(buffer)):
            (path, line, lsb) = buffer[i]
            lineAt = int(line)
            startLine = lineAt - 5
            if startLine<0:
                startLine = 0
            endLine = startLine + 10
            with open(path) as f:
                source = f.readlines()[startLine:endLine]
            content += '<table>\r\n\t<thead>\r\n\t\t<tr><td>File</td><td>'+path+'</td></tr>\r\n\t\t<tr><td>Line</td><td>'+line+'</td></tr>\r\n\t\t<tr><td>Lsb</td><td>'+lsb+'</td></tr>\r\n\t</thead>\r\n\t</tbody>'
            for i in range(0, len(source)):
                raw = source[i].rstrip("\r\n\t\s")
                raw = raw.replace("&", '&amp;')
                raw = raw.replace("\t", '    ')
                raw = raw.replace(" ", '&nbsp;')
                raw = raw.replace("<", '&lt;')
                raw = raw.replace(">", '&gt;')
                if lineAt-startLine-1==i:
                    raw = '<b>' + raw + '</b>'
                content += "\t\t<tr><td>" + str(startLine+i+1) + '</td><td>'+raw+'</td></tr>\r\n'
            content += '\t</tbody>\r\n</table>\r\n'

        # Fill template
        html = self._loadTemplate()
        html = html.replace('{errorType}', etype)
        html = html.replace('{errorMessage}', emessage)
        html = html.replace('{content}', content)

        return html


""" <template>
<!doctype html>
<html>
    <head>
        <style>
            body{
                position: absolute;
                display: block;
                width: 100%;
                background-color: #c0c0c0;
                margin: 0px;
                padding: 80px 20px 20px 20px;
                box-sizing: border-box;
                font-family: Arial;
            }
            h1{
                position: absolute;
                top: 0px;
                left: 0px;
                background-color: #f0f0f0;
                display: block;
                height: 60px;
                width: 100%;
                margin: 0px;
                padding: 0px 20px;
                line-height: 60px;
                color: #444444;
                font-size: 20px;
                box-sizing: border-box
            }
            h2{
                display: block;
                height: 30px;
                background-color: #f0f0f0;
                border-radius: 5px;
                margin: 0px 0px 20px 0px ;
                font-weight: normal;
                font-size: 16px;
                line-height: 30px;
                overflow: hidden;
            }
            h2 > b{
                display: inline-block;
                height: 30px;
                font-weight: normal;
                line-height: 30px;
                padding: 0px 10px 0px 20px;
                margin-right: 5px;
                background-color: #d9ab8a;
            }
            table{
                width           : 100%;
                border-spacing  : 0;
                border-collapse : collapse;
                font-size       : 11px;
                font-family     : "Courier New";
                margin-bottom   : 20px;
                border-radius   : 5px;
                background-color: #f0f0f0;
                overflow        : hidden;
            }
            table tr td{
                padding         : 2px 10px;
            }

            table thead tr td:first-child{
                width           : 40px;
                text-align      : right;
                background-color: #d9ab8a;
            }
            table thead tr:last-child td{
                border-bottom   : dotted 1px #888888
            }

            
            table tbody tr:nth-child(2n) td{
                background-color: #e0e0e0;
            }

            table tbody tr td:first-child{
                width           : 40px;
                text-align      : right;
                border-right    : dotted 1px #888888
            }
            table tbody tr td:nth-child(2){
                white-space     : nowrap;
            }
        </style>
    </head>
    <body>
        <h1>Nano framework error</h1>
        <h2><b>{errorType}</b> {errorMessage}</h2>
        {content}
    </body>
</html>
"""