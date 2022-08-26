class ControllerIndex:

	def __init__(self, Nano):
		self.Nano = Nano

	def e404(self):
		return self.Nano.View.Json(404, {"status": "Not found"}, {})

	def index(self):
		# Call another controller
		# return self.Nano.Controllers["ControllerIndex"].users()
		# Redirect to entrypoint asset
		return self.Nano.View.Redirect("/index.htm")

	def test(self, number):
		return self.Nano.View.Json(200, {"test": 3, "argv": number}, {})
		
	def users(self):
		users = self.Nano.Models["ModelTest"].listUsers()
		return self.Nano.View.Json(200, users, {})