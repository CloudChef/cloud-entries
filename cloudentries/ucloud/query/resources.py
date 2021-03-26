# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.ucloud.client import UcloudClient
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response, filter_output
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Resp
from cloudchef_integration.tasks.cloud_resources.ucloud.response import UcloudFilterResponse


@support_getattr
class UcloudResource(object):
    def __init__(self, connect_params, query_params=None):
        self.connect_params = self.prepare_params(connect_params)
        self.query_params = query_params

    @staticmethod
    def prepare_params(params):
        return {
            'base_url': params.get('base_url', 'https://api.ucloud.cn'),
            'public_key': params['access_key_id'],
            'private_key': params['access_key_secret'],
            'region': params.get('region')
        }

    @common_params(Params.Validation.Schema)
    @common_response(Resp.Validation.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def validation(self):
        if not self.connect_params.get('region'):
            self.connect_params['region'] = 'cn-sh2'
        resp = UcloudClient(
            **self.connect_params).validation(self.query_params)
        return resp

    @common_params(Params.Region.Schema)
    @common_response(Resp.Region.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def region(self):
        resp = UcloudClient(
            **self.connect_params).describe_region(self.query_params)
        return resp

    @common_params(Params.Zone.Schema)
    @common_response(Resp.Zone.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    @filter_output(UcloudFilterResponse.filter_region)
    def zone(self):
        resp = UcloudClient(
            **self.connect_params).describe_zone(self.query_params)
        return resp

    @common_params(Params.Image.Schema)
    @common_response(Resp.Image.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    @filter_output(UcloudFilterResponse.filter_image_name)
    @filter_output(UcloudFilterResponse.filter_os_type)
    def image(self):
        resp = UcloudClient(
            **self.connect_params).describe_image(self.query_params)
        return resp

    @common_params(Params.Instance.Schema)
    @common_response(Resp.Instance.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def instance(self):
        resp = UcloudClient(
            **self.connect_params).describe_uhost(self.query_params)
        return resp

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def volume(self):
        resp = UcloudClient(
            **self.connect_params).describe_disk(self.query_params)
        return resp

    @common_response(Resp.VolumeType.Schema)
    def volume_type(self):
        resp = UcloudClient(
            **self.connect_params).volume_type(self.query_params)
        return resp

    @common_params(Params.Snapshot.Schema)
    @common_response(Resp.Snapshot.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def snapshot(self):
        resp = UcloudClient(
            **self.connect_params).describe_snapshot(self.query_params)
        return resp

    @common_params(Params.Vpc.Schema)
    @common_response(Resp.Vpc.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def network(self):
        resp = UcloudClient(**self.connect_params).describe_vpc(self.query_params)
        return resp

    @common_params(Params.Subnet.Schema)
    @common_response(Resp.Subnet.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def subnet(self):
        resp = UcloudClient(
            **self.connect_params).describe_subnet(self.query_params)
        return resp

    @common_params(Params.Firewall.Schema)
    @common_response(Resp.Firewall.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def security_group(self):
        resp = UcloudClient(
            **self.connect_params).describe_firewall(self.query_params)
        return resp

    @common_params(Params.Eip.Schema)
    @common_response(Resp.Eip.Schema)
    @filter_output(UcloudFilterResponse.filter_resource)
    def eip(self):
        resp = UcloudClient(**self.connect_params).describe_eip(self.query_params)
        return resp
