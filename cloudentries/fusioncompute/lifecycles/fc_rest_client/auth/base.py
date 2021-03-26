# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
from ..exceptions import ValidationError


class Auth(object):
    SESSION_URI = "/service/session"

    def __init__(self,
                 base_url=None,
                 username=None,
                 password=None,
                 verify=False,
                 cert=None,
                 version="6.3"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.verify = verify
        self.cert = cert
        self.version = version

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json;version={0};charset=UTF-8".format(self.version),
            "Accept-Language": "en_US",
            "X-Auth-User": self.username,
            "X-Auth-Key": self.password,
        }

    def authorize(self):
        auth_url = self.base_url + self.SESSION_URI
        try:
            resp = requests.post(auth_url,
                                 headers=self.headers,
                                 verify=self.verify,
                                 cert=self.cert)
            if resp.status_code != 200:
                raise ValidationError(resp.content)
        except Exception as e:
            raise ValidationError(e)
        return resp

    def get_token(self):
        resp = self.authorize()
        token = resp.headers['X-Auth-Token']
        return token

    def get_auth_headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json;version={0};charset=UTF-8".format(self.version),
            "Accept-Language": "en_US",
            "X-Auth-Token": self.get_token()
        }
