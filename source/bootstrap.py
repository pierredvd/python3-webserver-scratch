#!/usr/local/bin/python3
import sys
import os
import json

DS = os.path.sep
DIR_ROOT = os.path.dirname(os.path.abspath(__file__)) + DS
sys.path.append(DIR_ROOT)

from nano.server import Server
from nano.applicatives import Applicatives
from nano.command import Command

apps = Applicatives(DIR_ROOT)
command = Command()

def start():
    server = Server(DIR_ROOT)
    server.onrequest(apps.run)

command.on("start", start)
command.on("list", lambda: (print(apps.list())))
command.on("app.test", lambda app: (apps.test(app)))
command.run()