# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response, filter_output
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Resp
from cloudchef_integration.tasks.cloud_resources.ksyun.response import KsyunFilterResponse
from .client import KsyunClient
import os


@support_getattr
class KsyunResource(object):
    def __init__(self, connection_params, query_params=None):
        """
        params: {
         "region": region,
         "ks_access_key_id": ks_access_key_id,
         "ks_secret_access_key": ks_secret_access_key
        }
        """
        self.connection_params = self.prepare_params(connection_params)
        self.query_params = query_params

    @staticmethod
    def prepare_params(params):
        return {
            'region': params.get('region'),
            'ks_access_key_id': params['access_key_id'],
            'ks_secret_access_key': params['access_key_secret'],
            'domain': params.get('domain', None)
        }

    @common_params(Params.Validation.Schema)
    @common_response(Resp.Validation.Schema)
    def validation(self):
        if not self.connection_params.get('region'):
            self.connection_params['region'] = os.environ.get('KSYUN_DEFAULT_REGION')
        return KsyunClient(**self.connection_params).describe_region(self.query_params)

    @common_params(Params.Region.Schema)
    @common_response(Resp.Region.Schema)
    def region(self):
        if not self.connection_params.get('region'):
            self.connection_params['region'] = os.environ.get('KSYUN_DEFAULT_REGION')
        return KsyunClient(**self.connection_params).describe_region(self.query_params)

    @common_params(Params.Zone.Schema)
    @common_response(Resp.Zone.Schema)
    def zone(self):
        return KsyunClient(**self.connection_params).describe_availability_zone(self.query_params)

    @common_params(Params.Image.Schema)
    @common_response(Resp.Image.Schema)
    @filter_output(KsyunFilterResponse.filter_image_name)
    @filter_output(KsyunFilterResponse.filter_os_type)
    def image(self):
        return KsyunClient(**self.connection_params).describe_images(self.query_params)

    @common_params(Params.Instance.Schema)
    @common_response(Resp.Instance.Schema)
    def instance(self):

        resp = KsyunClient(**self.connection_params).describe_instances(self.query_params)
        image_set = KsyunClient(**self.connection_params).describe_images({})
        image_os_dict = {image["Id"]: image["Platform"] for image in image_set}
        for instance in resp:
            instance['OperatingSystem'] = image_os_dict.get(instance.get('ImageId'))
        return resp

    @common_params(Params.Flavor.Schema)
    @common_response(Resp.Flavor.Schema)
    @filter_output(KsyunFilterResponse.filter_flavor)
    def flavor(self):
        zone_set = KsyunClient(**self.connection_params).describe_availability_zone(self.query_params)
        self.query_params['Zone'] = ','.join([zone["Id"] for zone in zone_set])
        return KsyunClient(**self.connection_params).describe_flavor(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Resp.Family.Schema)
    def family(self):
        return KsyunClient(**self.connection_params).describe_family(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    def local_volume(self):
        return KsyunClient(**self.connection_params).describe_local_volume(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    def cloud_volume(self):
        return KsyunClient(**self.connection_params).describe_volumes(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    def volume(self):
        '''
        金山云API：
        1.describe_instance_volumes只能查到Instance挂载的【云硬盘(ebs)】，可以根据InstanceId过滤
        2.describe_local_volumes 只能查到Instance挂载的【本地硬盘(local)】信息， 可以根据InstanceId过滤
        3.describe_volumes 只能查到所有的【云硬盘(ebs】,并且不能根据InstanceId过滤

        Java查询场景：
        1.根据InstanceId查询该Instance的所有硬盘信息   describe_local_volume + describe_instance_volumes
        2.根据volume_category查询所有的data/system的信息 describe_local_volume + describe_volumes
        :return:
        '''

        volumes = []
        if self.query_params.get("InstanceId"):  # 按InstanceId查询
            volumes.extend(KsyunClient(**self.connection_params).describe_local_volume(self.query_params))
            volumes.extend(KsyunClient(**self.connection_params).describe_instance_volumes(self.query_params))
            return volumes

        # 查询所有的系统/数据盘
        volumes.extend(KsyunClient(**self.connection_params).describe_local_volume(self.query_params))
        volumes.extend(KsyunClient(**self.connection_params).describe_volumes(self.query_params))
        return volumes

    @common_params(Params.Snapshot.Schema)
    @common_response(Resp.Snapshot.Schema)
    def snapshot(self):
        volumes = KsyunClient(**self.connection_params).describe_local_volume(self.query_params)
        volume_snapshots = []
        for volume in volumes:
            query_params = {"VolumeId": volume['Id']}
            volume_snapshots.extend(KsyunClient(**self.connection_params).describe_local_volume_snapshots(query_params))
        return volume_snapshots

    @common_params(Params.Vpc.Schema)
    @common_response(Resp.Vpc.Schema)
    def network(self):
        return KsyunClient(**self.connection_params).describe_vpcs(self.query_params)

    @common_params(Params.Subnet.Schema)
    @common_response(Resp.Subnet.Schema)
    def subnet(self):
        return KsyunClient(**self.connection_params).describe_subnets(self.query_params)

    @common_params(Params.Firewall.Schema)
    @common_response(Resp.Firewall.Schema)
    def security_group(self):
        return KsyunClient(**self.connection_params).describe_security_groups(self.query_params)

    @common_params(Params.Eip.Schema)
    @common_response(Resp.Eip.Schema)
    @filter_output(KsyunFilterResponse.filter_eip_state)
    def eip(self):
        return KsyunClient(**self.connection_params).describe_addresses(self.query_params)

    @common_params(Params.Flavor.Schema)
    @common_response(Resp.VolumeType.Schema)
    @filter_output(KsyunFilterResponse.filter_volume_type)
    def volume_type(self):
        '''
        Query volume type by flavor_id...
        ex: flavor_id: C4.8C
        '''
        if not self.query_params.get('category', ""):
            return [{'Id': 'SSD3.0', 'Name': 'SSD3.0'},
                    {'Id': 'EHDD', 'Name': 'EHDD'},
                    {'Id': "Local_SSD", "Name": "Local_SSD"}]

        return KsyunClient(**self.connection_params).describe_flavor(self.query_params)

    @common_params(Params.Volume.Schema)
    @common_response(Resp.Volume.Schema)
    def instance_volume(self):
        return KsyunClient(**self.connection_params).describe_instance_volumes(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Resp.Line.Schema)
    def line(self):
        return KsyunClient(**self.connection_params).get_lines(self.query_params)

    @property
    def resource_limit(self):
        disk_info = [{
            'disk': {
                'maxNum': 20,
                'sizeLimit': {
                    'SystemDisk': {
                        'maxSize': 500,
                        'minSize': 20,
                    },
                    'DataDisk': {
                        'maxSize': 32000,
                        'minSize': 10,
                    }
                }
            }
        }]
        return disk_info

    @common_params(Params.LbListener.Schema)
    @common_response(Resp.LbListener.Schema)
    def describe_listeners(self):
        return KsyunClient(**self.connection_params).describe_listeners(self.query_params)
