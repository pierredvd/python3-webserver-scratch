#!/usr/bin/env python3

import datetime
import json

class View:

    def __init__(self):
        self.code = 200
        self.body = ""
        self.headers = {}

    def set(code: int, body: str, headers: dict):
        self.code = code
        self.body = body
        self.headers = headers

    def _reset(self):
        self.code = 200
        self.body = ""
        self.headers = {}

    def _serializable(self, data):
        if isinstance(data, datetime.datetime):
            return int(datetime.datetime.timestamp(data))
        if isinstance(data, list):
            for i in range(len(data)):
                data[i] = self._serializable(data[i])
        if isinstance(data, dict):
            for key in data:
                data[key] = self._serializable(data[key])

        return data

    def Json(self, code, data, headers):
        self._reset()
        self.code = code
        self.body = json.dumps(self._serializable(data), sort_keys=True)
        for key in headers:
            self.headers[key] = headers[key]
        self.headers["contentType"] = "text/json; chatset: utf-8"
        self.headers["connection"] = "close"
        return self

    def Html(self, code, data, headers):
        self._reset()
        self.code = code
        self.body = data
        for key in headers:
            self.headers[key] = headers[key]
        self.headers["contentType"] = "text/html; chatset: utf-8"
        self.headers["connection"] = "keep-alive"
        return self

    def Redirect(self, url):
        self._reset()
        self.code = 302
        self.body = ""
        self.headers["location"] = url
        return self