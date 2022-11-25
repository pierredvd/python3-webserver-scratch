#!/usr/bin/env python3
from nano.config                    import Config
from nano.server.httprequest        import HttpRequest

"""
    Class for manage lang translations
"""
class Lang:

    """
        List translation files
        @param   directoryPath str    Path of main translations directory
        @returns None
    """
    def __init__(self, directoryPath: str):
        self._data               = Config(directoryPath)
        self._lang               = 'en'
        self._langs              = self._data.keys()
        if len(self._langs)>0 and self._lang not in self._langs:
            self._lang = self._langs[0]

    """
        Destructor empty internal data
        @returns None
    """
    def __del__(self):
        self._data = None

    """
        Ask update translations from files (as config update)
        @returns None
    """
    def update(self):
        self._data.update()

    """
        Ask update translations from files  and current lang from request
        @returns None
    """
    def updateFromRequest(self, request: HttpRequest):
        if "acceptLanguage" in request.headers:
            for accept in request.headers["acceptLanguage"].split(','):
                if len(accept)>=2:
                    wantedLang = accept[0:2]
                    if wantedLang in self._langs:
                        self._lang = wantedLang
                        break
        self._data.update()

    """
        Return current lang
        @returns lang str  Current lang
    """
    def getLang(self) -> str:
        return self._lang

    """
        Change current lang
        @returns lang str  Current lang
    """
    def setLang(self, lang: str):
        if not lang in self._langs:
            raise Exception("No transations available for lang \""+lang+"\"")
        self._lang = lang

    """
        Translate a key
        @param   xpath          str  Translation key
        @returns translation    str  Text mathing with key + lang
    """
    def translate(self, xpath: str) -> str:
        return self._data.get(self._lang+'.'+xpath, "<"+xpath+">")