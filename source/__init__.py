#!/usr/bin/env python3

from nano.server            import Server
from nano.app               import App

import os
import sys

if __name__ == '__main__':

    def currentDir():
        for path in [os.getcwd() + os.path.sep + sys.argv[0], sys.argv[0], os.path.abspath(__file__)]:
            if os.path.isfile(path):
                return os.path.dirname(os.path.abspath(path))+os.path.sep


    dirRoot = currentDir()      # Define root directory
    sys.path.append(dirRoot)    # Add it to package resolver

    apps   = App(dirRoot)       # Create applicatives manager
    # print(apps.list())
    server = Server(dirRoot)    # Create servers

    # Bind entering http request server to apps resolver
    server.on("request", lambda args: apps.resolve(args["request"], args["response"]))
