# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
import uuid

from cloudify import ctx
from cloudify.utils import convert2bool
from tencentcloud.cbs.v20170312.models import (
    Placement
)

from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from abstract_plugin.platforms.common.volume import CommonVolume
from abstract_plugin.platforms.tencentcloud.restclient import VolumeHelper
from abstract_plugin.platforms.tencentcloud.utils import Base
from abstract_plugin.platforms.common.constants import EXTERNAL_ID


class Volume(CommonVolume, Base):

    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    def _prepare_placement(self):
        placement = Placement()
        placement.Zone = self.resource_config.get('available_zone_id')
        return placement

    def _is_create_system_disk(self):
        '''
        System_disk has been created where instance was created
        We Just need to update runtime_properties.
        '''
        if not convert2bool(ctx.node.properties['resource_config'].get('is_system_disk')):
            return False
        instance_id = ctx.instance.relationships[0].target.instance.runtime_properties.get('external_id')
        volume_info = json.loads(VolumeHelper().describe_system_disk(instance_id).to_json_string())
        volume_id = volume_info['DiskId']
        ctx.instance.runtime_properties['disk_info'] = volume_info
        ctx.instance.runtime_properties['volume'] = {'size': volume_info['DiskSize']}
        ctx.instance.runtime_properties['volume_type'] = volume_info['DiskType']
        ctx.instance.runtime_properties['host_id'] = instance_id
        self.set_base_runtime_props(resource_id=volume_id, name=volume_info['DiskName'])
        return True

    def create(self, **kwargs):
        if self._is_create_system_disk():
            return
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not volume_id:
            client_token = ctx.instance.runtime_properties.get('ClientToken', uuid.uuid4().hex)
            request_body = {
                "DiskType": self.resource_config.get('volume_type'),
                'DiskChargeType': self.resource_config.get('DiskChargeType', 'POSTPAID_BY_HOUR'),
                'Placement': self._prepare_placement(),
                'DiskName': self.resource_config.get('name') or ctx.instance.id,
                'DiskSize': self.resource_config.get('size'),
                'ClientToken': client_token
            }
            ctx.logger.info('Creating tencentcloud volume with parameters: {}.'.format(request_body))
            if not ctx.instance.runtime_properties.get('ClientToken'):
                ctx.instance.runtime_properties['ClientToken'] = client_token
            volume = VolumeHelper().create_disk(request_body)
            volume_id = volume['DiskId']
            ctx.instance.runtime_properties['disk_info'] = volume
            ctx.instance.runtime_properties['volume'] = {'size': volume['DiskSize']}
            ctx.instance.runtime_properties['volume_type'] = volume['DiskType']
            self.set_base_runtime_props(resource_id=volume_id, name=volume['DiskName'])

        self.attach_volume(volume_id)
        ctx.logger.info('Volume {} created.'.format(volume_id))

    def delete(self, **kwargs):
        if ctx.node.properties['resource_config'].get('is_system_disk'):
            return
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not volume_id:
            return
        ctx.logger.info('Deleting tencentcloud volume {}.'.format(volume_id))
        self.detach_volume(volume_id)
        VolumeHelper().delete_disks([volume_id])
        clear_runtime_properties()
        ctx.logger.info('Volume {} deleted.'.format(volume_id))

    def attach_volume(self, volume_id, instance_id=None):
        vm_instance = self.get_related_vm()
        if not instance_id:
            instance_id = vm_instance.runtime_properties[EXTERNAL_ID]

        ctx.logger.info('Attaching volume {} to instance {}.'.format(volume_id, instance_id))
        VolumeHelper().attach_disks(instance_id, [volume_id])
        ctx.instance.runtime_properties['host_id'] = instance_id
        ctx.logger.info('Volume {} attached to instance {}.'.format(volume_id, instance_id))

    def detach_volume(self, volume_id, instance_id=None):
        if not instance_id:
            instance_id = self.get_related_vm().runtime_properties[EXTERNAL_ID]
        ctx.logger.info('Detaching volume {} from vm {}.'.format(volume_id, instance_id))
        VolumeHelper().detach_disks(instance_id, [volume_id])
        ctx.instance.runtime_properties['host_id'] = ''
        ctx.logger.info('Volume {} detached from instance {}.'.format(volume_id, instance_id))

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        instance_id = validate_parameter('server_id', kwargs)
        self.attach_volume(volume_id, instance_id)
        ctx.instance.runtime_properties['host_id'] = instance_id

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        instance_id = validate_parameter('server_id', kwargs)
        self.detach_volume(volume_id, instance_id)
        ctx.instance.runtime_properties['host_id'] = ''

    def custom_resize(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Resizing volume {}.'.format(volume_id))

        size = validate_parameter('size', kwargs)
        VolumeHelper().resize_disk(volume_id, size)
        ctx.logger.info('Volume {} resized to {} GB.'.format(volume_id, size))
        ctx.instance.runtime_properties['volume'] = {'size': size}
        ctx.instance.update()
