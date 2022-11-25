#!/usr/bin/env python3

from nano.app.controller import Controller

class ControllerWebsocket(Controller):

	def e404(self, send):
		send("Not found !")

	def index(self, send):

		#print(self.App.Lang.getLang())
		#self.App.Lang.setLang("fr")

		send(self.App.Lang.translate("websocket.helloworld"))

	def test(self, send, number):
		send("{\"test\": 3, \"argv\": "+number+"}")