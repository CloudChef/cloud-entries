# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import hashlib
import http.client
import json
import urllib.request
import urllib.parse
import urllib.error
import urllib.parse
from cloudify import ctx
from abstract_plugin.platforms.common.utils import validate_parameter
from cloudify.utils import decrypt_password
from cloudify.exceptions import NonRecoverableError


# 连接云平台
class UConnection(object):
    def __init__(self, base_url):
        self.base_url = base_url
        o = urllib.parse.urlsplit(base_url)
        if o.scheme == 'https':
            self.conn = http.client.HTTPSConnection(o.netloc)
        else:
            self.conn = http.client.HTTPConnection(o.netloc)

    def __del__(self):
        self.conn.close()

    def get(self, uri, params):
        uri += "?" + urllib.parse.urlencode(params)
        self.conn.request("GET", uri)
        response = json.loads(self.conn.getresponse().read())
        return response

    def post(self, uri, params):
        headers = {"Content-Type": "application/json"}
        self.conn.request("POST", uri, json.JSONEncoder().encode(params), headers)
        response = json.loads(self.conn.getresponse().read())
        return response


class UcloudApiClient(object):
    def __init__(self, params):
        self.region = validate_parameter('region', params)
        self.g_params = {'PublicKey': validate_parameter('access_key_id', params)}
        self.private_key = decrypt_password(validate_parameter('access_key_secret', params))
        base_url = params.get('base_url', 'https://api.ucloud.cn')
        self.conn = UConnection(base_url)

    def get(self, uri, params):
        _params = dict(self.g_params, **params)

        try:
            _params["Signature"] = _verfy_ac(self.private_key, _params)
        except Exception as e:
            ctx.logger.info(" ")
            raise NonRecoverableError("Connect to ucloud failed! the error message is {0}".format(e))
        return self.conn.get(uri, _params)

    def post(self, uri, params):
        _params = dict(self.g_params, **params)

        try:
            _params["Signature"] = _verfy_ac(self.private_key, _params)
        except Exception as e:
            ctx.logger.info(" ")
            raise NonRecoverableError("Connect to ucloud failed! the error message is {0}".format(e))
        return self.conn.post(uri, _params)


def _verfy_ac(private_key, params):
    items = sorted(params.items())

    params_data = ""
    for key, value in items:
        params_data = params_data + str(key) + str(value)

    params_data = params_data + private_key

    '''use sha1 to encode keys'''
    hash_new = hashlib.sha1()
    hash_new.update(params_data.encode('utf-8'))
    hash_value = hash_new.hexdigest()
    return hash_value
