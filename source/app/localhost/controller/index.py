#!/usr/bin/env python3

from nano.app.controller import Controller
from nano.app.view 		 import View

class ControllerIndex(Controller):

	def e404(self):
		return View().Json(404, {"status": "Not found"}, {})

	def index(self):

		self.App.Log.trace("hey ! je laisse une trace !")

		# Call another controller
		# return self.App.Controllers["ControllerIndex"].users()
		# Redirect to entrypoint asset

		#muc()

		return View().Redirect("/index.htm")

	def test(self, number):
		return View().Json(200, {"test": 3, "argv": number}, {})
		
	def users(self):
		try:
			users = self.App.Models["ModelUser"].listUsers()
			return View().Json(200, users, {})
		except Exception as e:
			return View().Json(503, {"error": str(e)}, {})