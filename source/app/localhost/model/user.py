
from nano.app.instance import Instance
from nano.app.model import Model

class ModelUser(Model):

    connexion = "postgresql-test"

    def listUsers(self) -> list:
        data = self.query("SELECT * FROM public.user")
        return data