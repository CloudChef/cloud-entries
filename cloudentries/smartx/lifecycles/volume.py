# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx

from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from abstract_plugin.platforms.common.volume import CommonVolume
from abstract_plugin.platforms.smartx.restclient import Client, VolumeHelper, ComputeHelper
from abstract_plugin.platforms.smartx.utils import Base
from abstract_plugin.platforms.common.constants import EXTERNAL_ID


optional_keys = ['volume_type', 'storage_policy_uuid', 'description']


class Volume(CommonVolume, Base):

    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    def create(self, **kwargs):
        if self._create_system_disk():
            return
        volume_category = self.resource_config.get('is_system_disk')
        if volume_category and str(volume_category).lower() == "true":
            ctx.logger.info("SmartX doesn't support system disk.")
            return
        try:
            target_instance = self.get_related_vm()
            server_id = target_instance.runtime_properties.get(EXTERNAL_ID)
            with ComputeHelper(Client()) as helper:
                vm_info = helper.get_vm(server_id)

            with VolumeHelper(Client()) as helper:

                if self.use_external_resource:
                    volume_id = validate_parameter('resource_id', self.resource_config)
                    ctx.logger.info('Use existed SmartX volume: {}.'.format(volume_id))
                else:
                    size = int(validate_parameter('size', self.resource_config))
                    size_in_byte = size << 30
                    volume_dict = {
                        "name": self.resource_config.get('name') or ctx.instance.id,
                        "size_in_byte": size_in_byte
                    }

                    self.set_optional_values(self.resource_config, volume_dict, optional_keys)

                    ctx.logger.info('Creating SmartX volume with parameters: {}'.format(volume_dict))
                    job_info = helper.create_volume(volume_dict)
                    helper.wait_job(job_info['job_id'])
                    volume_id = self.wait_job(helper, job_info['job_id'], resource_type='KVM_VOLUME')
                    ctx.logger.info('Create volume from SmartX successfully.')

                volume_info = helper.get_volume(volume_id)
                self.attach_volume(helper, vm_info, volume_info)

                extra_values = {'volume': {'size': size}, 'host_id': target_instance.id}
                self.save_runtime_properties('volume', volume_info, extra_values)
        except Exception as e:
            raise NonRecoverableError('Create volume from SmartX failed: {}.'.format(e))

    def _create_system_disk(self):
        volume_category = self.resource_config.get('is_system_disk')
        if (not volume_category) or str(volume_category).lower() == "false":
            return False
        ctx.logger.info("SmartX create system disk.")
        target_instance = self.get_related_vm()
        server_id = target_instance.runtime_properties.get(EXTERNAL_ID)
        with ComputeHelper(Client(**self.connection_config)) as helper:
            vm_info = helper.get_vm(server_id)
            ctx.logger.info('Create volume from SmartX successfully. vm_info:{}'.format(vm_info))
        volume_id = ""
        for volume in vm_info.get("disks"):
            if isinstance(volume, dict) and volume.get("type") == "disk":  # system disk
                volume_id = volume.get("volume_uuid")
                break
        if volume_id:
            with VolumeHelper(Client(**self.connection_config)) as helper:
                volume_info = helper.get_volume(volume_id)
                volume_size_byte = volume_info.get('size_in_byte') or volume_info.get('size')
                volume_size = volume_size_byte >> 30
                volume_info['size'] = volume_size
                extra_values = {'volume': {'size': volume_size}, 'host_id': target_instance.id}
                self.save_runtime_properties('volume', volume_info, extra_values)
        return True

    def delete(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('SmartX volume {} deleted.'.format(volume_id))
        if not volume_id:
            ctx.logger.warn('No SmartX volume id provided.')
            return
        try:
            ctx.logger.info('Deleting SmartX volume {}.'.format(volume_id))
            with VolumeHelper(Client()) as helper:
                volume_info = helper.get_volume(volume_id)
                target_instance = self.get_related_vm()
                vm_info = target_instance.runtime_properties.get('compute_info')

                self.detach_volume(helper, vm_info, volume_info)

                job_info = helper.delete_volume(volume_id)
                self.wait_job(helper, job_info['job_id'])
            ctx.logger.info('SmartX volume {} deleted.'.format(volume_id))
            clear_runtime_properties()
        except Exception as e:
            raise NonRecoverableError('Delete SmartX volume {} failed: {}'.format(volume_id, e))

    def attach_volume(self, helper, vm_info, volume_info):
        ctx.logger.debug(
            'Attaching volume {} to vm {}.'.format(volume_info['uuid'], vm_info['uuid']))
        disks = vm_info.get('disks')
        disk = {'type': 'disk', 'path': volume_info.get('path'), 'bus': 'virtio'}
        disks.append(disk)
        self._attach_volume(helper, vm_info, disks)

        ctx.logger.debug(
            'Attached volume {} to vm {}.'.format(volume_info['uuid'], vm_info['uuid']))

    def _attach_volume(self, helper, vm_info, disks, timeout=600, interval=15):
        remaining_time = timeout
        err = ""
        while remaining_time >= 0:
            try:
                return self.operate_volume('attach', helper, vm_info, disks)
            except Exception as err:
                if "JOB_RESOURCE_IS_LOCKED" in str(err):
                    time.sleep(interval)
                    remaining_time -= interval
                else:
                    break
        raise NonRecoverableError(err)

    def detach_volume(self, helper, vm_info, volume_info):
        ctx.logger.debug(
            'Detaching volume {} from vm {}.'.format(volume_info['uuid'], vm_info['uuid']))

        disks = vm_info.get('disks')
        for item in disks:
            if item.get('path') == volume_info.get('path'):
                disks.remove(item)
                break
        self.operate_volume('detach', helper, vm_info, disks)

        ctx.logger.debug(
            'Detached volume {} from vm {}.'.format(volume_info['uuid'], vm_info['uuid']))

    def operate_volume(self, action, helper, vm_info, disks):
        vm_id = vm_info['uuid']
        try:
            job_info = helper.update_disks(vm_id, disks)
            job_status = helper.wait_job(job_info['job_id'])
            if job_status == "failed":
                job_detail = helper.get_job(job_info['job_id'])
                raise Exception(job_detail['task_list'])
        except Exception as e:
            raise NonRecoverableError("{} volume with vm {} failed: {}.".format(action.title(), vm_id, e))

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        server_id = kwargs.get('server_id')

        with ComputeHelper(Client()) as helper:
            vm_info = helper.get_vm(server_id)

        with VolumeHelper(Client()) as helper:
            volume_info = helper.get_volume(volume_id)
            self.attach_volume(helper, vm_info, volume_info)
        size_in_byte = volume_info.get("size_in_byte") or volume_info.get("size")
        size = int(size_in_byte) >> 30
        extra_values = {'volume': {'size': size}}
        self.save_runtime_properties('volume', extra_values=extra_values)

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        server_id = kwargs.get('server_id')

        with ComputeHelper(Client()) as helper:
            vm_info = helper.get_vm(server_id)

        with VolumeHelper(Client()) as helper:
            volume_info = helper.get_volume(volume_id)
            self.detach_volume(helper, vm_info, volume_info)

    def custom_resize(self, **kwargs):

        volume_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        size = validate_parameter('size', kwargs)
        size_in_byte = int(size) << 30
        data = {'size_in_byte': size_in_byte}
        if kwargs.get('description'):
            data['description'] = kwargs['description']
        ctx.logger.debug('Resizing volume {} with parameters {}.'.format(volume_id, data))
        try:
            with VolumeHelper(Client()) as helper:
                volume_info = helper.get_volume(volume_id)
                volume_name = volume_info.get("name")
                if not volume_name:
                    ctx.logger.error('Resizing volume {} failed. volume_name is required'.format(volume_id))
                    return
                data.update({
                    "name": volume_name
                })
                helper.update_volume(volume_id, data)
        except Exception as e:
            raise NonRecoverableError('Resize volume {} failed: {}.'.format(volume_id, e))
        extra_values = {'volume': {'size': size}}
        self.save_runtime_properties('volume', extra_values=extra_values)
        ctx.logger.debug('Resized volume {}'.format(volume_id))
