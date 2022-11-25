
#!/usr/bin/env python3

from nano.app.test import Test

class ControllerIndexTest(Test):

	def __init__(self, Nano):
		self.Nano = Nano

	def Test_ControllerIndex(self):

		# Call another controller
		# return self.Nano.Controllers["ControllerIndex"].users()

		return True