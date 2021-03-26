# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import os
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response, filter_output
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Resp
from cloudchef_integration.tasks.cloud_resources.smartx.response import SmartXFilterResponse
from cloudchef_integration.tasks.cloud_resources.smartx.client import Client, Connection


@support_getattr
class SmartXResource(object):
    def __init__(self, connect_params, query_params=None):
        host = connect_params.get('host')
        port = int(connect_params.get('port')) or 443
        username = connect_params.get('username')
        password = connect_params.get('password')
        protocol = connect_params.get('protocol') or 'https'

        self.conn = Connection(protocol, host, port, username, password)
        self.query_params = query_params

    @common_params(Params.EmptyDesc.Schema)
    @common_response(Resp.Validation.Schema)
    def validation(self):
        self.conn.get_token()
        return []

    @common_params(Params.EmptyDesc.Schema)
    @common_response(Resp.Vpc.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    def network(self):
        with Client(self.conn) as client:
            return client.list_vdses(self.query_params)

    @common_params(Params.EmptyDesc.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    def storage_policy(self):
        with Client(self.conn) as client:
            return client.list_storage_policies(self.query_params)

    @common_params(Params.EmptyDesc.Schema)
    @common_response(Resp.Image.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    @filter_output(SmartXFilterResponse.filter_image_name)
    def image(self):
        with Client(self.conn) as client:
            return client.list_templates(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    @filter_output(SmartXFilterResponse.filter_volume_type)
    def volume(self):
        with Client(self.conn) as client:
            if self.query_params.get('InstanceId'):
                return client.get_vm(self.query_params)
            else:
                return client.list_volumes(self.query_params)

    @property
    def volume_type(self):
        """
           SmartX has no volume type, return fake data for compatibility
        """
        return self.storage_policy

    @common_params(Params.EmptyDesc.Schema)
    @common_response(Resp.Subnet.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    def subnet(self):
        with Client(self.conn) as client:
            return client.list_networks(self.query_params)

    @common_params(Params.EmptyDesc.Schema)
    @common_response(Resp.Instance.Schema)
    @filter_output(SmartXFilterResponse.filter_resource)
    def instance(self):
        with Client(self.conn) as client:
            return client.list_vms(self.query_params)
