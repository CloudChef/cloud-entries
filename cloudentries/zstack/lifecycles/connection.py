# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import hashlib
import json
import time

from abstract_plugin.platforms.common.connector import Connector
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password


class ZStackConnection(object):
    def __init__(self, url, username, password):
        self.username = username
        self.password = password
        self.seesion_id = None
        self.headers = {'Content-Type': 'application/json'}
        self.url = url

    def login(self):
        payload = {
            "logInByAccount": {
                "password": hashlib.sha512(self.password.encode('utf-8')).hexdigest(),
                "accountName": self.username
            }
        }
        r = requests.put(self.url + '/accounts/login', headers=self.headers, data=json.dumps(payload))
        return r

    def get_session_id(self):
        return self.login().json()['inventory']['uuid']

    def patch_header(self):
        self.seesion_id = self.get_session_id()
        self.headers['Authorization'] = 'OAuth ' + self.seesion_id

    @staticmethod
    def check_response_code(r):
        if int(r.status_code) in (400, 404, 405, 500, 503):
            raise Exception(
                "query failed, the error message is {0}, the status code is {1}".format(r.text, r.status_code))

    def prepare_params(self, params):
        m = ["q={k}={v}".format(k=k, v=v) for k, v in list(params.items()) if v]
        return "&".join(m)

    def common_request(self, method, endpoint, body=None, condition=None, rpc=False):
        url = self.url + endpoint
        if condition and condition.get('resource_id'):
            url = url + '/' + condition['resource_id']
            del condition['resource_id']
        if rpc is True:
            url = url + "/actions"
        if condition:
            params = self.prepare_params(condition)
            url = url + "?" + params
        resp = getattr(requests, method)(url, headers=self.headers, data=json.dumps(body))
        self.check_response_code(resp)
        return resp

    def common_polling(self, location, times=1800):
        resp = requests.get(location, headers=self.headers)
        if int(resp.status_code) == 202 or times <= 0:
            ctx.logger.info("Wait for the result of the asynchronous call to return. left {0} times".format(times))
            time.sleep(2)
            times -= 1
            return self.common_polling(location, times)
        else:
            return resp

    def open_session(self):
        self.seesion_id = self.get_session_id()
        self.headers['Authorization'] = 'OAuth ' + self.seesion_id

    def close_session(self):
        url = self.url + '/accounts/sessions/' + self.seesion_id
        resp = requests.delete(url)
        self.check_response_code(resp)

    def call(self, method, endpoint, body=None, condition=None, rpc=False):
        self.open_session()
        resp = self.common_request(method, endpoint, body, condition, rpc)
        if resp.json().get('location'):
            location = resp.json()['location']
            resp = self.common_polling(location)
            self.check_response_code(resp)
        self.close_session()
        return resp


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()
        self.connection = self.connection_config
        self.client = self.get_client()

    def get_client(self):
        try:
            return ZStackConnection(**self.prepare_connection())
        except Exception as e:
            raise NonRecoverableError("login zstack error, the error message is {0}".format(e))

    def prepare_connection(self):
        return {
            'url': self.connection['url'],
            'username': self.connection['username'],
            'password': decrypt_password(self.connection['password']),
        }
