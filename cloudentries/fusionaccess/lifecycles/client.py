# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import json
from .constants import SUCCESS_CODE
import hashlib
from abstract_plugin.platforms.common.connector import Connector
from cloudify.utils import decrypt_password


class FusionAccessConnect(Connector):
    def __init__(self, **kwargs):
        super(FusionAccessConnect, self).__init__()
        self.host = self.connection_config.get("host")
        self.port = self.connection_config.get("port")
        self.protocol = self.connection_config.get("protocol")
        self.username = self.connection_config.get("username")
        self.password = decrypt_password(self.connection_config.get("password"))
        self.basic_uri = "/services/ita"

    def gen_url(self, uri=""):
        return "{}://{}:{}{}{}".format(self.protocol, self.host, self.port, self.basic_uri, uri)

    def encrypt(self):
        return hashlib.sha256(self.password.encode('utf-8')).hexdigest()

    def gen_token(self):
        headers = {
            'Content-Type': 'application/json',
            'X-Auth-User': self.username,
            'X-Auth-Key': self.encrypt()
        }
        url = self.gen_url(uri="/login")
        rep = requests.request("post", url, headers=headers, verify=False)
        if (not rep) or (rep.status_code not in [200]) or (not rep.headers) or (not rep.headers.get("X-Auth-Token")):
            raise Exception("Request Cloud API generate token failed, msg:{}".format(rep))
        return rep.headers.get("X-Auth-Token")

    def common_request(self, method, uri="", params={}, token_name="X-Auth-Token", verify=False,
                       success_code=SUCCESS_CODE):
        headers = {
            'Content-Type': 'application/json'
        }
        url = self.gen_url(uri)
        token = self.gen_token()
        if token:
            headers.update({token_name: token})
        params.update({
            "operatorId": self.username
        })
        rep = requests.request(method, url, headers=headers, json=params, verify=verify)
        content = rep.content
        if content and (not isinstance(content, dict)):
            content = json.loads(content)
        if rep.status_code not in success_code:
            raise Exception("Request Cloud API failed, msg:{}".format(rep))
        result_code = content.get("resultCode")
        if int(result_code) != 0:
            raise Exception("Request Cloud API failed, result_code:{}, msg:{}".format(result_code, content))
        return content

    def describe_job(self, task_id):
        params = {
            "jobId": task_id
        }
        url = "/describeJobDetailInfo"
        job_info = self.common_request("post", url, params)
        job_ret_code = job_info.get("resultCode")
        if job_ret_code != 0:
            raise Exception("Request Cloud API describe job: {} failed, msg:{}".format(task_id, job_info))
        for job in job_info.get("jobDetailInfoList", {}):
            if job.get("jobID") == task_id:
                return job
        return {}
