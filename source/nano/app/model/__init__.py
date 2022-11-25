#!/usr/bin/env python3

from nano.app.instance           import Instance

import sys

try:
    import psycopg2               
    import psycopg2.extras
except ImportError:
    pass

"""
    Abstract Class for models
"""
class Model:


    """
        Constructor
        @param parent Instance  Applicative instance (endpoint of a vhosts)
        @return None
    """
    def __init__(self, parent: Instance):

        if self.__class__.__name__=="Model":
            raise Exception("Model must be inherits")

        self._config    = {}
        self._connexion = None

        connexions  = parent.Config.get("databases")
        connexion = type(self).connexion
        if not connexion in connexions:
            raise Exception("Model \""+__class__.__name__+"\" connexion \""+connexion+"\" not found in database configuration")

        self._config    = connexions[connexion]
 
    """
        Destructor, close runing connexions
        @return None
    """
    def __del__(self):
        self.close()

    """
        Run sql query on current model
        @param  query   str     SQL Query
        @return None
    """
    def query(self, sql) -> list:

        # Connect
        if self._connexion==None:
            if not "driver" in self._config:
                raise "Model \""+self.__class__.__name__+"\" config require \"driver\""

            if self._config["driver"]=="psycopg2":

                # Postgres through psycopg2
                if not "psycopg2" in sys.modules.keys():
                    raise ImportError("Model \""+self.__class__.__name__+"\" require module \"psycopg2\", use \"pip install psycopg2\"")

                self._connexion = psycopg2.connect(
                    host    = self._config["host"],
                    dbname  = self._config["database"],
                    user    = self._config["user"],
                    password= self._config["password"],
                    port    = self._config["port"]
                )

            else :
                raise Exception("Model \""+self.__class__.__name__+"\" driver \""+self._config["driver"]+"\" unknown")

        # Execute and format result
        cursor = self._connexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        data = []
        datamap = {} 
        for record in records:
            data.append(dict(record))
        return data

    """
        Close current connexion
        @return None
    """
    def close(self):
        if self._connexion != None:
            self._connexion.close()
            self._connexion = None