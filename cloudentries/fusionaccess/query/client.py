# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import json
from cloudchef_integration.tasks.cloud_resources.fusionaccess.constants import SUCCESS_CODE
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from cloudchef_integration.tasks.cloud_resources.fusionaccess.response import FusionAccessStandardResponse
from . import params as FaParams
import hashlib


class FusionAccessConnect(object):
    def __init__(self, protocol, host, port, username, password="", **kwargs):
        """
        :param protocol: http | https type: string
        :param host: type: string
        :param port: type: int
        :param base_url: url common prefix,if need type: string
        :param kwargs:
        :return:
        """
        self.host = host
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password
        self.basic_uri = "/services/ita"

    def gen_url(self, uri=""):
        return "{}://{}:{}{}{}".format(self.protocol, self.host, self.port, self.basic_uri, uri)

    def encrypt(self):
        return hashlib.sha256(self.password.encode('utf-8')).hexdigest()

    def gen_token(self):
        """
        Request generate token method if token is needed.
        """
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
        """
        :param method: get | post | put | delete type: string
        :param uri: request's suffer uri if need, type: string
        :param params: request's params if need, type: dict
        :param token_name: add token in header if need, type: string
        :param verify: True | False verify https or not, type: bool
        :param success_code: eg:[200], type: list
        :return:
        """
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
        return content


class FusionAccessClient(object):
    def __init__(self, protocol, host, port, username, password="", **kwargs):
        self.conn = FusionAccessConnect(protocol, host, port, username, password, **kwargs)

    @convert_params(EmptyDesc.Schema)
    @convert_response(FusionAccessStandardResponse.validation)
    def validation(self, query_params):
        return self.conn.gen_token()

    @convert_params(EmptyDesc.Schema)
    @convert_response(FusionAccessStandardResponse.site)
    def describe_site(self, query_params):
        uri = "/describeSites"
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.ClusterDesc.Schema)
    @convert_response(FusionAccessStandardResponse.cluster)
    def describe_cluster(self, query_params):
        uri = "/describeClusters"
        return self.conn.common_request('post', uri, query_params)

    @convert_response(FusionAccessStandardResponse.instance)
    def describe_instance(self, params):
        uri = "/describeInstancesInfo"
        query_params = {
            "siteId": params.get("region"),
            "param": {}
        }
        if params.get("resource_id"):
            query_params["param"].update({
                "instanceIds": params.get("resource_id").split(",")
            })
        if params.get("zone"):
            if isinstance(params.get("zone"), int):
                query_params["param"].update({
                    "clusterIds": [params.get("zone")]
                })
            elif isinstance(params.get("zone"), str):
                query_params["param"].update({
                    "clusterIds": params.get("zone").split(",")
                })
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.TemplateDesc.Schema)
    @convert_response(FusionAccessStandardResponse.template)
    def describe_template(self, query_params):
        uri = "/describeTemplatesInfo"
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.DatastoreDesc.Schema)
    @convert_response(FusionAccessStandardResponse.datastore)
    def describe_datastore(self, query_params):
        uri = "/describeDatastoreInfo"
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.DatastoreTemplateDesc.Schema)
    @convert_response(FusionAccessStandardResponse.datastore_by_template)
    def describe_datastore_by_template(self, query_params):
        uri = "/queryDatastoresByTemplate"
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.SecuritygroupDesc.Schema)
    @convert_response(FusionAccessStandardResponse.securitygroup)
    def describe_securitygroup(self, query_params):
        uri = "/describeSecurityGroups"
        return self.conn.common_request('post', uri, query_params)

    @convert_params(FaParams.TemplateDesc.Schema)
    @convert_response(FusionAccessStandardResponse.portgroup)
    def describe_portgroup(self, query_params):
        uri = "/describePortGroups"
        return self.conn.common_request('post', uri, query_params)
