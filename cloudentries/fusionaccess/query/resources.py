# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.fusionaccess.client import FusionAccessClient
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Response
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import filter_output, FilterResponse


@support_getattr
class FusionAccessResource(object):
    def __init__(self, connect_params, query_params=None):
        self.connect_params = self.prepare_params(connect_params)
        self.query_params = query_params

    @staticmethod
    def prepare_params(connect_params):
        return {
            'protocol': connect_params.get('protocol', ''),
            'host': connect_params.get('host', ''),
            'port': connect_params.get('port', ''),
            'username': connect_params.get('username', ''),
            'password': connect_params.get('password', ''),
        }

    @property
    def validation(self):
        resp = FusionAccessClient(
            **self.connect_params).validation(self.query_params)
        return resp

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Region.Schema)
    def region(self):
        resp = FusionAccessClient(
            **self.connect_params).describe_site(self.query_params)
        return resp

    @common_params(Params.Zone.Schema)
    @common_response(Response.Zone.Schema)
    def zone(self):
        resp = FusionAccessClient(
            **self.connect_params).describe_cluster(self.query_params)
        return resp

    @common_params(Params.Instance.Schema)
    @common_response(Response.Instance.Schema)
    def instance(self):
        resp = FusionAccessClient(
            **self.connect_params).describe_instance(self.query_params)
        return resp

    @common_params(Params.VolumeType.Schema)
    @common_response(Response.VolumeType.Schema)
    @filter_output(FilterResponse.filter_resource)
    def volume_type(self):
        if self.query_params.get('instanceType') and self.query_params.get('region'):
            resp = FusionAccessClient(
                **self.connect_params).describe_datastore_by_template(self.query_params)
        else:
            resp = FusionAccessClient(
                **self.connect_params).describe_datastore(self.query_params)
        return resp

    @property
    def network(self):
        resp = FusionAccessClient(**self.connect_params).describe_portgroup(self.query_params)
        return resp

    @common_params(Params.Firewall.Schema)
    @common_response(Response.Firewall.Schema)
    def security_group(self):
        resp = FusionAccessClient(
            **self.connect_params).describe_securitygroup(self.query_params)
        return resp

    @common_params(Params.VolumeType.Schema)
    @common_response(Response.Flavor.Schema)
    def flavor(self):
        resp = FusionAccessClient(
            **self.connect_params).describe_template(self.query_params)
        return resp

    @common_params(Params.VolumeType.Schema)
    @common_response(Response.Flavor.Schema)
    def image(self):
        return self.flavor
