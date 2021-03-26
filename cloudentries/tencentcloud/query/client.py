# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from cloudchef_integration.tasks.cloud_resources.tencentcloud.response import TencentStandardResponse
from cloudchef_integration.tasks.cloud_resources.tencentcloud import params as TencentParams
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client
from tencentcloud.cvm.v20170312.models import (
    DescribeZonesRequest,
    DescribeImagesRequest,
    DescribeInstanceTypeConfigsRequest,
    DescribeRegionsRequest,
    DescribeInstancesRequest,
    DescribeInstanceVncUrlRequest
)
from tencentcloud.vpc.v20170312 import vpc_client
from tencentcloud.vpc.v20170312.models import (
    DescribeSecurityGroupsRequest,
    DescribeVpcsRequest,
    DescribeSubnetsRequest
)
from tencentcloud.cbs.v20170312 import cbs_client
from tencentcloud.cbs.v20170312.models import DescribeDisksRequest, DescribeSnapshotsRequest, Filter as CbsFilter
from tencentcloud.cbs.v20170312.models import DescribeDiskConfigQuotaRequest
from tencentcloud.billing.v20180709 import billing_client


class TencentClient(object):

    def __init__(self, secretId, secretKey):
        self.cred = credential.Credential(secretId, secretKey)

    def execute_request(self, func, request_class, **kwargs):
        try:
            req = request_class()
            for key, value in list(kwargs.items()):
                setattr(req, key, value)
            return func(req)
        except TencentCloudSDKException as err:
            raise


class ComputeTencentClient(TencentClient):

    def __init__(self, secretId, secretKey, region):
        super(ComputeTencentClient, self).__init__(secretId, secretKey)
        self.client = cvm_client.CvmClient(self.cred, region)

    @convert_params(EmptyDesc.Schema)
    @convert_response(TencentStandardResponse.region)
    def list_regions(self, params):
        return self.execute_request(self.client.DescribeRegions, DescribeRegionsRequest, **params).RegionSet

    @convert_params(EmptyDesc.Schema)
    @convert_response(TencentStandardResponse.zone)
    def list_zones(self, params):
        return self.execute_request(self.client.DescribeZones, DescribeZonesRequest, **params).ZoneSet

    @convert_params(TencentParams.InstanceDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.instance)
    def list_instances(self, params):
        return self.execute_request(self.client.DescribeInstances, DescribeInstancesRequest, **params).InstanceSet

    @convert_params(TencentParams.VncDesc.Schema)
    def instance_vnc_url(self, params):
        return self.execute_request(self.client.DescribeInstanceVncUrl, DescribeInstanceVncUrlRequest,
                                    **params).InstanceVncUrl

    @convert_params(TencentParams.FlavorDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.flavor)
    def list_instance_types(self, params):
        return self.execute_request(self.client.DescribeInstanceTypeConfigs, DescribeInstanceTypeConfigsRequest,
                                    **params).InstanceTypeConfigSet

    @convert_params(TencentParams.ImageDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.image)
    def list_images(self, params):
        return self.execute_request(self.client.DescribeImages, DescribeImagesRequest, **params).ImageSet


class NetworkTencentClient(TencentClient):

    def __init__(self, secretId, secretKey, region):
        super(NetworkTencentClient, self).__init__(secretId, secretKey)
        self.client = vpc_client.VpcClient(self.cred, region)

    @convert_params(TencentParams.SecurityGroupDesc.Schema)
    @convert_response(TencentStandardResponse.security_group)
    def list_security_groups(self, params):
        return self.execute_request(self.client.DescribeSecurityGroups, DescribeSecurityGroupsRequest,
                                    **params).SecurityGroupSet

    @convert_params(TencentParams.NetworkDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.network)
    def list_networks(self, params):
        return self.execute_request(self.client.DescribeVpcs, DescribeVpcsRequest, **params).VpcSet

    @convert_params(TencentParams.SubnetDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.subnet)
    def list_subnets(self, params):
        return self.execute_request(self.client.DescribeSubnets, DescribeSubnetsRequest, **params).SubnetSet


class DiskTencentClient(TencentClient):

    def __init__(self, secretId, secretKey, region):
        super(DiskTencentClient, self).__init__(secretId, secretKey)
        self.client = cbs_client.CbsClient(self.cred, region)
        self.compute_clinet = cvm_client.CvmClient(self.cred, region)

    @convert_params(TencentParams.DiskDesc.Schema, convert_method=TencentParams.TencentConvertParams)
    @convert_response(TencentStandardResponse.volume)
    def list_volumes(self, params):
        return self.execute_request(self.client.DescribeDisks, DescribeDisksRequest, **params).DiskSet

    def is_cloud_disk(self, disk):
        disk_types = ('CLOUD_BASIC', 'CLOUD_SSD', 'CLOUD_PREMIUM')
        return True if disk.DiskType in disk_types else False

    def prepare_snapshots_filters(self, instance_id):
        query_params = {'InstanceIds': [instance_id]}
        instance = self.execute_request(
            self.compute_clinet.DescribeInstances, DescribeInstancesRequest, **query_params).InstanceSet[0]
        system_disk = instance.SystemDisk
        data_disks = instance.DataDisks or []

        disk_ids = []
        if self.is_cloud_disk(system_disk):
            disk_ids.append(system_disk.DiskId)
        for data_disk in data_disks:
            if self.is_cloud_disk(data_disk):
                disk_ids.append(data_disk.DiskId)

        filter = CbsFilter()
        filter.Name = 'disk-id'
        filter.Values = disk_ids
        return {"Filters": [filter]}

    @convert_params(EmptyDesc.Schema)
    @convert_response(TencentStandardResponse.snapshot)
    def list_snapshots(self, params):
        query_params = self.prepare_snapshots_filters(params.get('InstanceId'))
        return self.execute_request(self.client.DescribeSnapshots, DescribeSnapshotsRequest, **query_params).SnapshotSet

    @convert_params(TencentParams.VolumeTypeDesc.Schema)
    @convert_response(TencentStandardResponse.volume_type)
    def list_volume_types(self, params):
        return self.execute_request(self.client.DescribeDiskConfigQuota, DescribeDiskConfigQuotaRequest,
                                    **params).DiskConfigSet


class AccountTencentClient(TencentClient):
    def __init__(self, secretId, secretKey):
        super(AccountTencentClient, self).__init__(secretId, secretKey)
        self.client = billing_client.BillingClient(self.cred, None)

    @convert_params(TencentParams.BalanceDesc.Schema)
    @convert_response(TencentStandardResponse.balance)
    def describe_account_balance(self, params):
        from tencentcloud.billing.v20180709 import models
        return self.execute_request(self.client.DescribeAccountBalance, models.DescribeAccountBalanceRequest, **params)
