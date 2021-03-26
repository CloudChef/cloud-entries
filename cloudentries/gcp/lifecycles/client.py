# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import httplib2
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter
from cloudify.utils import decrypt_password
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build


class GCPConnect(object):
    def __init__(self, params, api_name, api_version):
        self.api_name = api_name
        self.api_version = api_version
        self.key_id = validate_parameter('private_key_id', params)
        self.private_key = decrypt_password(validate_parameter('private_key', params)).replace('\\n', '\n')
        self.project = validate_parameter('project_id', params)
        self.client_email = validate_parameter('client_email', params)
        self.client_id = validate_parameter('client_id', params)
        self.key_json = self.generate_key_json()
        self.scope = ['https://www.googleapis.com/auth/' + api_name]

    def generate_key_json(self):
        key_json = {
            "type": "service_account",
            "project_id": self.project,
            "private_key_id": self.key_id,
            "private_key": self.private_key,
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        return key_json

    def connection(self):
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(self.key_json, self.scope)
            # FIXME: This is the company's HTTP proxy, which needs to be removed later
            http = credentials.authorize(
                httplib2.Http(proxy_info=httplib2.ProxyInfo(httplib2.socks.PROXY_TYPE_SOCKS5, '192.168.1.16', 1089),
                              disable_ssl_certificate_validation=True))
            client = build(self.api_name, self.api_version, http=http)

            return client
        except Exception as e:
            raise NonRecoverableError("Connect to Google Cloud failed! the error message is {0}".format(e))
