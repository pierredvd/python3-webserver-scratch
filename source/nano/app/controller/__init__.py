#!/usr/bin/env python3

from nano.app.instance           import Instance

"""
    Abstract Class for controllers
"""
class Controller():

    """
        Constructor
        @param   parent             Applicative     Applicative object
        @returns None
    """
    def __init__(self, parent: Instance):

        if self.__class__.__name__=="Controller":
            raise Exception("Controller must be inherits")

        self.App = parent
