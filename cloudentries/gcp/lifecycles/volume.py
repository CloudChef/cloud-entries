# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json

from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties, drop_none
from abstract_plugin.platforms.common.volume import CommonVolume
from . import constants
from abstract_plugin.platforms.gcp.base import Base


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    def get_volume_state(self, compute, volume_id):
        return self.describe_volume(compute, volume_id)['status']

    def get_target_instance_and_id(self):
        target_instance = self.get_related_vm()
        if target_instance:
            instance_id = target_instance.runtime_properties['external_id']

            return target_instance, instance_id

    def _prepare_request_config(self, compute):
        volume_type = validate_parameter('volume_type', self.resource_config)
        volume_response = compute.diskTypes().get(
            project=self.project,
            zone=self.zone,
            diskType=volume_type).execute()
        volume_self_link = volume_response.get('selfLink')
        volume_name = self.resource_config.get('volume_name') or ctx.instance.id

        config = {
            "name": volume_name.replace('_', '-').lower(),
            "description": self.resource_config.get('description'),
            "sizeGb": validate_parameter('size', self.resource_config),
            "type": volume_self_link,
            "physicalBlockSizeBytes": '4096',
        }

        return drop_none(config)

    def _create_external_volume(self, compute):
        if not self.use_external_resource:
            return False

        ctx.logger.info('Create an existed FusionCompute disk: {}.'.format(
            self.resource_id))

        volume_info = self.describe_volume(compute, self.resource_id)
        self.save_runtime_properties('volume', volume_info)
        return True

    def create(self):
        # Creates a persistent disk in the specified project using the data in the request.
        compute = self.get_client()
        if self._create_external_volume(compute):
            return

        ctx.logger.info(
            'Creating volume by resource config: {}'.format(
                json.dumps(self.resource_config, indent=2)))

        volume_body = self._prepare_request_config(compute)
        ctx.logger.info('Volume is creating, the body is {}.'.format(volume_body))

        try:
            operation = compute.disks().insert(
                project=self.project,
                zone=self.zone,
                body=volume_body).execute()
            self._wait_for_operation(compute, self.project, self.zone, operation['name'])
        except Exception as e:
            raise NonRecoverableError(
                'Create volume failed! The params of create volume is {0},'
                'the error message is {1}'.format(volume_body, e)
            )

        volume_id = volume_body['name']
        volume_info = self.describe_volume(compute, volume_id)
        self.save_runtime_properties('volume', volume_info)

        # Attaches an existing Disk resource to an instance.
        target_instance, vm_id = self.get_target_instance_and_id()

        self.attach_volume(compute, vm_id, volume_id)

        server_instance_id = target_instance.id
        size = validate_parameter('size', self.resource_config)
        extra_values = {'volume': {'size': size}}
        self.save_runtime_properties('volume', volume_info, extra_values)
        self.write_vm_info(compute, vm_id, server_instance_id)

    def delete(self):
        # Deletes the specified persistent disk.
        compute = self.get_client()

        volume_id = ctx.instance.runtime_properties['external_id']
        vm_id = ctx.instance.runtime_properties.get('vm_id')
        ctx.logger.info('Detach Volume {} from {}.'.format(volume_id, vm_id))
        # Detaches a disk from an instance.
        if vm_id:
            self.detach_volume(compute, vm_id, volume_id)

        volume_info = self.describe_volume(compute, volume_id)

        if not volume_info:
            ctx.logger.info('The volume has been deleted.')
        elif volume_info['status'] == constants.GCP_VOLUME_STATE_AVAILABLE:
            try:
                operation = compute.disks().delete(
                    project=self.project,
                    zone=self.zone,
                    disk=volume_id).execute()
                self._wait_for_operation(compute, self.project, self.zone, operation['name'])
            except Exception as e:
                raise NonRecoverableError(
                    'Delete volume {0} failed, the error message is {1}'.format(volume_id, e))

        clear_runtime_properties()
        self.remove_vm_info()

    def attach_volume(self, compute, vm_id, volume_id):
        volume_info = self.describe_volume(compute, volume_id)
        volume_link = volume_info['selfLink']
        attached_disk_body = {
            'type': 'PERSISTENT',
            'mode': 'READ_WRITE',
            'source': volume_link,
            'boot': False,
            'autoDelete': True,
        }
        ctx.logger.info(
            'Attaching volume {0} to instance {1}.'.format(volume_id, vm_id)
        )

        try:
            operation = compute.instances().attachDisk(
                project=self.project,
                zone=self.zone,
                instance=vm_id,
                body=attached_disk_body).execute()
            self._wait_for_operation(compute, self.project, self.zone, operation['name'])

        except Exception as e:
            raise NonRecoverableError(
                'Attach volume with instance {0} failed: {1}'.format(vm_id, e))

        ctx.logger.info(
            'Attached volume {0} to vm {1}.'.format(volume_id, vm_id)
        )

    def get_device_name(self, compute, vm_id, volume_id):
        volume_info = self.describe_volume(compute, volume_id)
        vm_info = self.describe_instance(compute, vm_id)

        if not volume_info['users']:
            ctx.logger.info('The disk is not bound to any of the virtual machines.')
            return

        disks = vm_info['disks']
        for disk in disks:
            if disk['source'] == volume_info['selfLink']:
                return disk['deviceName']

        ctx.logger.info('The disk is not bound to the virtual machines.')
        return

    def detach_volume(self, compute, vm_id, volume_id):
        device_name = self.get_device_name(compute, vm_id, volume_id)
        if not device_name:
            return

        try:
            operation = compute.instances().detachDisk(
                project=self.project,
                zone=self.zone,
                instance=vm_id,
                deviceName=device_name).execute()

            self._wait_for_operation(compute, self.project, self.zone, operation['name'])
        except Exception as e:
            raise NonRecoverableError(
                'Attach volume with instance {0} failed: {1}'.format(vm_id, e))

        ctx.logger.info(
            'Detached volume {0} to vm {1}.'.format(volume_id, vm_id)
        )

    def resize_volume(self, compute, volume_id, size):
        volume_state = self.get_volume_state(compute, volume_id)
        if volume_state != constants.GCP_VOLUME_STATE_AVAILABLE:
            raise NonRecoverableError('The volume is currently doing other operations,'
                                      'Volume {} current state is {}'.format(volume_id, volume_state))

        disks_resize_request_body = dict(sizeGb=size)
        try:
            compute.disks().resize(
                project=self.project,
                zone=self.zone,
                disk=volume_id,
                body=disks_resize_request_body).execute()
        except Exception as e:
            raise NonRecoverableError("Resize volume {0} failed! the error message is {1}".format(volume_id, e))

        extra_values = {'volume': {'size': size}}
        volume_info = self.describe_volume(compute, volume_id)
        self.save_runtime_properties('volume', volume_info, extra_values)

    def custom_attach(self, **kwargs):
        compute = self.get_client()
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        server_instance_id = validate_parameter('server_instance_id', kwargs)
        self.attach_volume(compute, server_id, volume_id)
        self.write_vm_info(compute, server_id, server_instance_id)

    def custom_detach(self, **kwargs):
        compute = self.get_client()
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('vm_id', ctx.instance.runtime_properties)
        self.detach_volume(compute, server_id, volume_id)
        self.remove_vm_info()

    def custom_resize(self, **kwargs):
        compute = self.get_client()
        volume_id = ctx.instance.runtime_properties['external_id']
        size = validate_parameter('size', kwargs)
        self.resize_volume(compute, volume_id, size)

    @staticmethod
    def remove_vm_info():
        ctx.instance.runtime_properties.update({
            'vm_id': None,
            'vm_info': None,
            'host_id': None
        })
        ctx.instance.update()

    def write_vm_info(self, compute, vm_id, server_instance_id):
        vm = self.describe_instance(compute, vm_id)
        ctx.instance.runtime_properties.update({
            'vm_id': vm_id,
            'vm_info': vm,
            'host_id': server_instance_id
        })
        ctx.instance.update()
