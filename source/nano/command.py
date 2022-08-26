from collections.abc import Callable
import sys
class Command():
    
    def __init__(self):

        self._handlers = {
            "start"      : [],
            "list"       : [],
            "app.vhost"  : [],
            "app.config" : [],
            "app.test"   : []
        }

    def on(self, eventName: str, callback: Callable):
        if eventName in self._handlers:
            self._handlers[eventName].append(callback)

    def run(self):

        if len(sys.argv)==2:
            if sys.argv[1]=="--start":
                for f in self._handlers["start"]:
                    f()
                return

        if len(sys.argv)==2:
            if sys.argv[1]=="--list":
                for f in self._handlers["list"]:
                    f()
                return

        if len(sys.argv)==3:
            if sys.argv[2]=="--test":
                for f in self._handlers["app.test"]:
                    f(sys.argv[1])
                return

        self._help(sys.argv[0])

    def _help(self, scriptname):

        print("")
        print("Usage: "+scriptname+" <option> | --start | --help | --list | [ app_name [ command | --vhost | --test ] ]")
        print("")
        print("    "+scriptname+" --start               Start server")
        print("    "+scriptname+" --help                Show help")
        print("    "+scriptname+" --list                List applicatives (event no vhosts)")
        print("    "+scriptname+" <app_name> --test     Run app test")
        print("")
        print("")   