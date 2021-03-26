# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import support_getattr
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import common_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import common_response, filter_output
from cloudchef_integration.tasks.cloud_resources.commoncloud import params as Params
from cloudchef_integration.tasks.cloud_resources.commoncloud import response as Response
from .client import ZstackClient
from .response import ZstackFilterResponse


@support_getattr
class ZstackResource(object):
    def __init__(self, connection_params, query_params=None):
        self.conection_params = connection_params
        self.query_params = query_params

    @property
    def validation(self):
        return self.instance

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Instance.Schema)
    @filter_output(ZstackFilterResponse.filter_resource)
    def instance(self):
        instance_list = ZstackClient(self.conection_params).describe_vm(self.query_params)
        image_list = ZstackClient(self.conection_params).describe_image(self.query_params)
        image_os_mapper = {}
        for image in image_list:
            image_os_mapper[image['Id']] = image['Name']
        for instance in instance_list:
            instance["OperatingSystem"] = image_os_mapper[instance['ImageId']]
        return instance_list

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Volume.Schema)
    @filter_output(ZstackFilterResponse.filter_instance)
    @filter_output(ZstackFilterResponse.filter_volume_type)
    def volume(self):
        return ZstackClient(self.conection_params).describe_volume(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Snapshot.Schema)
    def snapshot(self):
        '''
        1.先查所有snapshot
        2.查该云主机下的所有硬盘
        3.根据云硬盘过滤snapshot
        '''
        snapshots = ZstackClient(self.conection_params).describe_snapshot(self.query_params)
        if self.query_params.get('vmId'):
            volume_id_set = {volume.get('Id') for volume in self.volume()}
            snapshots = [snapshot for snapshot in snapshots if snapshot.get('VolumeId') in volume_id_set]
        return snapshots

    @common_params(Params.Image.Schema)
    @common_response(Response.Image.Schema)
    @filter_output(ZstackFilterResponse.filter_resource)
    @filter_output(ZstackFilterResponse.filter_image_name)
    def image(self):
        return ZstackClient(self.conection_params).describe_image(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Flavor.Schema)
    @filter_output(ZstackFilterResponse.filter_flavor)
    def flavor(self):
        return ZstackClient(self.conection_params).describe_flavor(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Vlan.Schema)
    def network(self):
        return ZstackClient(self.conection_params).describe_vlan(self.query_params)

    @common_params(Params.Subnet.Schema)
    @common_response(Response.Subnet.Schema)
    def subnet(self):
        return ZstackClient(self.conection_params).describe_subnet(self.query_params)

    @common_params(Params.Vpc.Schema)
    @common_response(Response.Vpc.Schema)
    def vpc(self):
        return ZstackClient(self.conection_params).describe_vpc(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Firewall.Schema)
    def security_group(self):
        return ZstackClient(self.conection_params).describe_security_group(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Vlan.Schema)
    def vlan(self):
        return ZstackClient(self.conection_params).describe_vlan(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.Vxlan.Schema)
    def vxlan(self):
        return ZstackClient(self.conection_params).describe_vxlan(self.query_params)

    @common_params(EmptyDesc.Schema)
    @common_response(Response.VolumeType.Schema)
    def volume_type(self):
        return ZstackClient(self.conection_params).describe_volume_type(self.query_params)

    @property
    def resource_limit(self):
        volume_type = ZstackClient(self.conection_params).describe_volume_type(self.query_params)
        if not volume_type:
            return []
        disk_size = volume_type[0].get('Size')
        disk_info = [{
            'disk': {
                'sizeLimit': {
                    'SystemDisk': {
                        'maxSize': disk_size,
                        'minSize': disk_size,
                    },
                    'DataDisk': {
                        'maxSize': disk_size,
                        'minSize': disk_size,
                    }
                }
            }
        }]
        return disk_info
