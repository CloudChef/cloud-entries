# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import os
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response, filter_output, \
    FilterResponse
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Resp
from cloudchef_integration.tasks.cloud_resources.tencentcloud.client import ComputeTencentClient
from cloudchef_integration.tasks.cloud_resources.tencentcloud.client import NetworkTencentClient
from cloudchef_integration.tasks.cloud_resources.tencentcloud.client import DiskTencentClient
from cloudchef_integration.tasks.cloud_resources.tencentcloud.client import AccountTencentClient

from cloudchef_integration.tasks.cloud_resources.tencentcloud import constants


@support_getattr
class TencentResource(object):
    def __init__(self, connect_params, query_params=None):
        self.query_params = query_params
        self.secretId = connect_params.get('access_key_id')
        self.secretKey = connect_params.get('access_key_secret')
        self.region_name = self.query_params.get('region') or os.environ.get('TENCENTCLOUD_REGION')

    @common_params(Params.Zone.Schema)
    @common_response(Resp.Zone.Schema)
    def validation(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_zones(self.query_params)

    @common_params(Params.Region.Schema)
    @common_response(Resp.Region.Schema)
    @filter_output(FilterResponse.filter_resource)
    def region(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_regions(self.query_params)

    @common_params(Params.Zone.Schema)
    @common_response(Resp.Zone.Schema)
    @filter_output(FilterResponse.filter_resource)
    def zone(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_zones(self.query_params)

    @common_params(Params.Instance.Schema)
    @common_response(Resp.Instance.Schema)
    def instance(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        instances = []
        offset = 0
        while True:
            self.query_params.update({"Offset": offset * 100})
            resp = client.list_instances(self.query_params)
            instances.extend(resp)
            if len(resp) < 100:
                break
            offset += 1
        return instances

    @common_params(Params.Firewall.Schema)
    @common_response(Resp.Firewall.Schema)
    def security_group(self):
        client = NetworkTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_security_groups(self.query_params)

    @common_params(Params.Vpc.Schema)
    @common_response(Resp.Vpc.Schema)
    def network(self):
        client = NetworkTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_networks(self.query_params)

    @common_params(Params.Snapshot.Schema)
    @common_response(Resp.Snapshot.Schema)
    def snapshot(self):
        client = DiskTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_snapshots(self.query_params)

    @common_params(Params.Image.Schema)
    @common_response(Resp.Image.Schema)
    @filter_output(FilterResponse.filter_image_name)
    @filter_output(FilterResponse.filter_os_type)
    def image(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_images(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    def volume(self):
        client = DiskTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_volumes(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.VolumeType.Schema)
    def volume_type(self):
        client = DiskTencentClient(self.secretId, self.secretKey, self.region_name)
        if self.query_params.get('instanceType'):
            instance_type = self.query_params.get('instanceType')
            instance_family = instance_type.split('.')[0]  # S5.LARGE8 -> S5
            category = self.query_params.get('category')
            disk_usage = ""
            if category == 'dataDisk':
                disk_usage = 'DATA_DISK'
            elif category == 'systemDisk':
                disk_usage = 'SYSTEM_DISK'
            params = {
                "region": self.query_params.get('region'),
                "zone": self.query_params.get('zone'),
                "instance_family": instance_family,
                "disk_usage": disk_usage
            }
            return client.list_volume_types(params)
        else:
            return [{"Id": "CLOUD_PREMIUM", "Name": "CLOUD_PREMIUM"},
                    {"Id": "CLOUD_SSD", "Name": "CLOUD_SSD"},
                    {"Id": "CLOUD_HSSD", "Name": "CLOUD_HSSD"}]

    @common_params(Params.Subnet.Schema)
    @common_response(Resp.Subnet.Schema)
    def subnet(self):
        client = NetworkTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_subnets(self.query_params)

    @common_params(Params.Flavor.Schema)
    @common_response(Resp.Flavor.Schema)
    @filter_output(FilterResponse.filter_flavor)
    def flavor(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        return client.list_instance_types(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Resp.Family.Schema)
    def family(self):
        family = []
        for type, machine_type in list(constants.INSTANCE_TYPE.items()):
            dic = {}
            dic['Id'] = '/'.join(machine_type)
            dic['Name'] = type
            family.append(dic)
        return family

    @property
    def remote_console_url(self):
        client = ComputeTencentClient(self.secretId, self.secretKey, self.region_name)
        result = client.instance_vnc_url(self.query_params)
        url_prefix = 'https://img.qcloud.com/qcloud/app/active_vnc/index.html?InstanceVncUrl='
        return [{'url': url_prefix + result}]

    @property
    def security_group_templates(self):
        templates = [
            {
                "Id": "放通全部端口",
                "Name": "暴露全部端口到公网和内网，有一定安全风险",
                "Ingress": [
                    {
                        "Action": "ACCEPT",
                    }
                ],
                "Egress": [
                    {
                        "Action": "ACCEPT",
                    }
                ]

            },
            {
                "Id": "放通22，80，443，3389端口和ICMP协议",
                "Name": "公网放通云主机常用登录及web服务端口，内网全放通。",
                "Ingress": [
                    {
                        "Port": "3389",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通Windows远程登录",
                        "Protocol": "tcp",
                    },
                    {
                        "Port": "22",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通Linux SSH登录",
                        "Protocol": "tcp",
                    },
                    {
                        "Port": "80,443",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通Web服务端口",
                        "Protocol": "tcp",
                    },
                    {
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通Ping服务",
                        "Protocol": "icmp",
                    },
                    {
                        "CidrBlock": "10.0.0.0/8",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通内网",
                    },
                    {
                        "CidrBlock": "172.16.0.0/12",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通内网",
                    },
                    {
                        "CidrBlock": "192.168.0.0/16",
                        "Action": "ACCEPT",
                        "PolicyDescription": "放通内网",
                    }
                ],
                "Egress": [
                    {
                        "Action": "ACCEPT",
                    }
                ]
            },
        ]
        return templates

    @property
    def resource_limit(self):
        disk_info = [{
            'disk': {
                'maxNum': 20,
                'sizeLimit': {
                    'CLOUD_PREMIUM': {
                        'maxSize': 32000,
                        'minSize': 10,
                    },
                    'CLOUD_HSSD': {
                        'maxSize': 32000,
                        'minSize': 20,
                    },
                    'CLOUD_SSD': {
                        'maxSize': 32000,
                        'minSize': 20,
                    },
                    'SystemDisk': {
                        'maxSize': 500,
                        'minSize': 50,
                    }
                }
            }
        }]
        return disk_info

    @common_params(EmptyDesc.Schema)
    @common_response(Resp.Balance.Schema)
    def balance(self):
        client = AccountTencentClient(self.secretId, self.secretKey)
        return client.describe_account_balance()
