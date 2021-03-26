# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import hashlib
import json
import time


class ZStackConnection(object):
    def __init__(self, username, password, url):
        self.username = username
        self.password = password
        self.session_id = None
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
        self.session_id = self.get_session_id()
        self.headers['Authorization'] = 'OAuth ' + self.session_id

    @staticmethod
    def check_response_code(r):
        if int(r.status_code) in (400, 404, 405, 500, 503):
            raise Exception(
                "query failed, the error message is {0}, the status code is {1}".format(r.text, r.status_code))

    def prepare_params(self, params):
        if params.get('resourceBundleId'):
            del params['resourceBundleId']
        m = ["q={k}={v}".format(k=k, v=v) for k, v in list(params.items()) if v]
        return "&".join(m)

    def common_request(self, method, endpoint, body=None, condition=None):
        url = self.url + endpoint
        if condition:
            if condition.get('resource_id'):
                url = url + '/' + condition['resource_id']
                del condition['resource_id']
            params = self.prepare_params(condition)
            url = url + "?" + params
        resp = getattr(requests, method)(url, headers=self.headers, data=json.dumps(body))
        self.check_response_code(resp)
        return resp

    def common_polling(self, location, times=1800):
        resp = requests.get(location, headers=self.headers)
        if int(resp.status_code) == 202 or times <= 0:
            time.sleep(2)
            times -= 1
            return self.common_polling(location, times)
        else:
            return resp

    def open_session(self):
        self.session_id = self.get_session_id()
        self.headers['Authorization'] = 'OAuth ' + self.session_id

    def close_session(self):
        url = self.url + '/accounts/sessions/' + self.session_id
        resp = requests.delete(url)
        self.check_response_code(resp)

    def call(self, method, endpoint, body=None, condition=None):
        self.open_session()
        resp = self.common_request(method, endpoint, body, condition)
        if method in ('post', 'put'):
            location = resp.json()['location']
            resp = self.common_polling(location)
            self.check_response_code(resp)
        self.close_session()
        return resp
