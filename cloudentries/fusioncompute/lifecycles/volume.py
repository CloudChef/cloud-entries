# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
import json

from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from abstract_plugin.platforms.common.volume import CommonVolume
from abstract_plugin.platforms.common import constants as common_constants
from abstract_plugin.platforms.fusioncompute.base import Base
from abstract_plugin.platforms.common import utils
from . import constants as fc_constants


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.fc_client = self.get_client()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    def get_system_disk_datastore(self, instance_id):
        instance_info = self.fc_client.servers.get(instance_id)
        return instance_info['vmConfig']['disks'][0]['datastoreUrn']

    def get_target_instance_and_id(self):
        target_instance = self.get_related_vm()
        if target_instance:
            instance_id = target_instance.runtime_properties['external_id']

            return target_instance, instance_id

    def _prepare_request_params(self):
        target_instance, instance_id = self.get_target_instance_and_id()
        volume_name = self.resource_config.get('volume_name') or ctx.instance.id
        params = {
            'name': volume_name,
            'type': validate_parameter('volume_type', self.resource_config),
            'quantityGB': validate_parameter('size', self.resource_config),
            'datastoreUrn': self.get_system_disk_datastore(instance_id),
            'isThin': True,
        }
        return utils.drop_none(params)

    def create(self):
        if self._create_external_volume():
            return

        ctx.logger.info(
            'Creating volume by resource config: {}'.format(
                json.dumps(self.resource_config, indent=2)))

        params = self._prepare_request_params()
        region_urn = validate_parameter('region', self.resource_config)
        ctx.logger.info('Volume is creating, the params is {}.'.format(params))

        try:
            volume_id = self.fc_client.volumes.create(region_urn, params)['urn']
        except Exception as e:
            raise NonRecoverableError(
                'Create volume failed! The params of create volume is {0},'
                'the error message is {1}'.format(params, e)
            )

        self.wait_for_target_state(volume_id, fc_constants.FC_VOLUME_STATE_AVAILABLE)

        volume_info = self.fc_client.volumes.get(volume_id)
        self.update_runtime_properties('volume', volume_info)

        target_instance, instance_id = self.get_target_instance_and_id()

        self.attach_volume(instance_id, volume_id)

        server_instance_id = target_instance.runtime_properties.get(common_constants.EXTERNAL_HOSTNAME)
        size = validate_parameter('size', self.resource_config)
        extra_values = {'volume': {'size': size}}
        self.update_runtime_properties('volume', volume_info, extra_values)
        self.write_vm_info(instance_id, server_instance_id)

    def delete(self):
        volume_id = ctx.instance.runtime_properties['external_id']
        instance_id = ctx.instance.runtime_properties.get('vm_id')
        ctx.logger.info('Detach Volume {} from {}.'.format(volume_id, instance_id))
        if instance_id and self.is_mounted(instance_id, volume_id):
            self.detach_volume(instance_id, volume_id)

        volume_info = self.fc_client.volumes.get(volume_id)

        if not volume_info:
            ctx.logger.info('The volume has been deleted.')
        elif volume_info['status'] == fc_constants.FC_VOLUME_STATE_AVAILABLE:
            try:
                self.fc_client.volumes.delete(volume_id)
            except Exception as e:
                raise NonRecoverableError(
                    'Delete volume {0} failed, the error message is {1}'.format(volume_id, e))

        clear_runtime_properties()
        self.remove_vm_info()

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        server_instance_id = validate_parameter('server_instance_id', kwargs)
        self.attach_volume(server_id, volume_id)
        self.write_vm_info(server_id, server_instance_id)

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        self.detach_volume(server_id, volume_id)
        self.remove_vm_info()

    def custom_resize(self, **kwargs):
        ctx.logger.info('runtime_properties: {}'.format(ctx.instance.runtime_properties))
        volume_id = ctx.instance.runtime_properties['external_id']
        size = validate_parameter('size', kwargs)
        size = size * 1024  # transfer to MB
        vm_id = ctx.instance.runtime_properties['vm_id']   # '/service/sites/3F4B0701/vms/i-0000029B'
        self.resize_volume(volume_id, size, vm_id)

    def attach_volume(self, instance_id, volume_id):
        volume_info = self.fc_client.volumes.get(volume_id)
        instance_info = self.fc_client.servers.get(instance_id)
        ctx.logger.info(
            'Attaching volume {0} to instance {1}.'.format(volume_info['uuid'], instance_info['uuid'])
        )

        try:
            self.fc_client.servers.attachvol(instance_id, volume_id)
        except Exception as e:
            raise NonRecoverableError(
                'Attach volume with instance {0} failed: {1}'.format(instance_info['uuid'], e))

        ctx.logger.info(
            'Attached volume {0} to vm {1}.'.format(volume_info['uuid'], instance_info['uuid']))

    def detach_volume(self, instance_id, volume_id):
        volume_info = self.fc_client.volumes.get(volume_id)
        instance_info = self.fc_client.servers.get(instance_id)
        ctx.logger.info(
            'Attaching volume {0} to instance {1}.'.format(volume_info['uuid'], instance_info['uuid'])
        )

        try:
            self.fc_client.servers.detachvol(instance_id, volume_id)
            self.wait_detach_volume(instance_id, volume_id)
        except Exception as e:
            raise NonRecoverableError(
                'Detach volume with instance {0} failed: {1}'.format(instance_info['uuid'], e))

        ctx.logger.info(
            'Detached volume {0} to vm {1}.'.format(volume_info['uuid'], instance_info['uuid']))

    def resize_volume(self, volume_id, size, vm_id):
        volume_info = self.describe_volume(volume_id)
        ctx.logger.info('urn: {}'.format(volume_info['urn']))

        volume_state = self.get_volume_state(volume_id)
        if volume_state != fc_constants.FC_VOLUME_STATE_AVAILABLE:
            raise NonRecoverableError('The volume is currently doing other operations,'
                                      'Volume {} current state is {}'.format(volume_id, volume_state))
        params = {
            'size': int(size),
            'volUrn': volume_info['urn']
        }
        try:
            self.fc_client.volumes.expandvol(vm_id, params)
        except Exception as e:
            ctx.logger.info('resize volume-id:{}, param:{} ,error:{}'.format(volume_id, params, e))
            raise NonRecoverableError("Resize volume {0} failed! the error message is {1}".format(volume_id, e))

        extra_values = {'volume': {'size': int(size / 1024)}}   # transfer to GB
        volume_info = self.fc_client.volumes.get(volume_id)
        self.update_runtime_properties('volume', volume_info, extra_values)

    def _create_external_volume(self):
        if not self.use_external_resource:
            return False

        ctx.logger.info('Create an existed FusionCompute disk: {}.'.format(
            self.resource_id))

        volume_info = self.fc_client.volumes.get(self.resource_id)
        self.update_runtime_properties('volume', volume_info)
        return True

    def describe_volume(self, volume_id):
        try:
            res = self.fc_client.volumes.get(volume_id)
            return res
        except Exception as e:
            raise NonRecoverableError("Failed to query information of volume {0}, "
                                      "the error message is {1}".format(volume_id, e))

    def get_volume_state(self, volume_id):
        volume_info = self.describe_volume(volume_id)
        return volume_info['status']

    def wait_for_target_state(self, volume_id, target_state, timeout=600, sleep_insterval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            volume_state = self.get_volume_state(volume_id)
            ctx.logger.info('Waiting for volume "{0}" to be {1}. current state: {2}'
                            .format(volume_id, target_state, volume_state))

            if isinstance(target_state, tuple):
                if volume_state in target_state:
                    return
            else:
                if volume_state == target_state:
                    return
            time.sleep(sleep_insterval)
        raise NonRecoverableError("Waiting volume to target state failed! the current "
                                  "state is {0}, the target state is {1}".format(volume_state, target_state))

    def wait_detach_volume(self, instance_id, volume_id, timeout=600, sleep_insterval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            if not self.is_mounted(instance_id, volume_id):
                return
            time.sleep(sleep_insterval)
        raise NonRecoverableError("Waiting detach volume {} from instance {} failed!".format(volume_id, instance_id))

    def is_mounted(self, instance_id, volume_id):
        instance_info = self.fc_client.servers.get(instance_id)
        disks_info = instance_info['vmConfig'].get('disks')
        for disk_info in disks_info:
            if disk_info['volumeUrn'] == volume_id:
                return True
        else:
            return False

    @staticmethod
    def remove_vm_info():
        ctx.instance.runtime_properties.update({
            'vm_id': None,
            'vm_info': None,
            'host_id': None
        })
        ctx.instance.update()

    def write_vm_info(self, vm_id, server_instance_id):
        vm = self.fc_client.servers.get(vm_id)
        ctx.instance.runtime_properties.update({
            'vm_id': vm_id,
            'vm_info': vm,
            'host_id': server_instance_id
        })
        ctx.instance.update()
