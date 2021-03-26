# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import time
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from cloudchef_integration.tasks.cloud_resources.smartx.response import SmartXStandardResponse
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.smartx.params import VolumeDesc


class Connection(object):

    def __init__(self, protocol, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._protocol = protocol

    def _gen_url(self, path, is_v3=False):
        if path.startswith("/"):
            path = path[1:]

        return "{protocol}://{host}:{port}/api/{version}/{path}".format(
            protocol=self._protocol,
            host=self.host,
            port=self.port,
            version="v3" if is_v3 else "v2",
            path=path
        )

    def get_token(self):
        res = requests.post(
            url=self._gen_url("/sessions", True),
            json={"username": self.username, "password": self.password},
            verify=False
        )
        res.raise_for_status()
        return res.json()["token"]

    def release(self, token):
        if token:
            requests.delete(
                url=self._gen_url("/sessions", True),
                headers={"Grpc-Metadata-Token": token},
                verify=False
            )

    def common_request(self, method, path="", token="", verify=False, **kwargs):
        """
        :param method: get | post | put | delete type: string
        :param uri: request's suffer uri if need, type: string
        :param params: request's params if need, type: dict
        :param token_name: add token in header if need, type: string
        :param verify: True | False verify https or not, type: bool
        :param success_code: eg:[200], type: list
        :return:
        """
        if not token:
            token = self.get_token()
        headers = {
            'X-SmartX-Token': token
        }
        url = self._gen_url(path)
        rep = requests.request(method, url, headers=headers, json=kwargs, verify=verify)
        rep.raise_for_status()
        return rep.json()


class Client(object):
    def __init__(self, connection):
        self.conn = connection
        self._token = None

    @staticmethod
    def check_r(r):
        if r.get("ec") != "EOK":
            raise Exception(r)
        return r.get("data")

    def __enter__(self):
        self._token = self.conn.get_token()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.release(self._token)
        self._token = None

    def get_job(self, job_id):
        return self.check_r(self.conn.common_request("get", "/jobs/{}".format(job_id), token=self._token))["job"]

    def wait_job(self, job_id):
        job = self.get_job(job_id)
        while job["state"] not in ("done", "failed"):
            time.sleep(5)
            job = self.get_job(job_id)
        return job['state']

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.network)
    def list_vdses(self, params):
        return self.check_r(self.conn.common_request("get", "/network/vds", token=self._token))

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.subnet)
    def list_networks(self, params):
        return self.check_r(self.conn.common_request("get", "/network/vm_vlans/search", token=self._token))['entities']

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.image)
    def list_templates(self, params):
        return self.check_r(self.conn.common_request("get", "/vm_templates", token=self._token)).get('entities', [])

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.storage_policy)
    def list_storage_policies(self, params):
        return self.check_r(self.conn.common_request("get", "/storage_policies", token=self._token))

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.volume)
    def list_volumes(self, params):
        return self.check_r(self.conn.common_request("get", "/volumes", token=self._token)).get('entities', [])

    @convert_params(EmptyDesc.Schema)
    @convert_response(SmartXStandardResponse.instance)
    def list_vms(self, params):
        return self.check_r(self.conn.common_request("get", "/vms", token=self._token)).get('entities', [])

    @convert_params(VolumeDesc.Schema)
    @convert_response(SmartXStandardResponse.vm_volume)
    def get_vm(self, params):
        vm_uuid = params.get("InstanceId")
        return self.check_r(self.conn.common_request("get", "/vms/{}".format(vm_uuid), token=self._token)).get('disks')
