class ModelTest:

    def __init__(self, Nano):
        self.connexion = "postgresql-test"
        self.Nano = Nano

    def listUsers(self) -> list:
        data = self.Nano.Model.query(connexion=self.connexion, sql="SELECT * FROM public.user")
        return data