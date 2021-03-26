# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import convert2bool
from abstract_plugin.platforms.common.utils import validate_parameter, drop_none
from . import constants
from abstract_plugin.platforms.common.volume import CommonVolume
from .base import Base
from .compute import Compute
from abstract_plugin.platforms.ksyun.restclient import Helper


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    @staticmethod
    def write_vm_info(vm_id):
        ctx.instance.runtime_properties.update({
            'host_id': vm_id
        })
        ctx.instance.update()

    def prepare_params(self):
        params = {
            'VolumeName': self.resource_config.get('name') or ctx.instance.id,
            'VolumeType': validate_parameter('volume_type', self.resource_config),
            'VolumeDesc': self.resource_config.get('volume_description'),
            'Size': validate_parameter('size', self.resource_config),
            'AvailabilityZone': validate_parameter('available_zone_id', self.resource_config),
            'ChargeType': self.resource_config.get('charge_type') or 'HourlyInstantSettlement',
            'PurchaseTime': self.resource_config.get('purchase_time') or 0,
        }
        return drop_none(params)

    def describe_volume(self, volume_id=None):
        params = {"VolumeId.1": volume_id} if volume_id else {}
        res = Helper().execute_request('ebs', 'describe_volumes', params)
        ctx.logger.info('describe volume, id: {}，parmas:{}, ret:{}'.format(volume_id, params, res))
        if volume_id and res['Volumes']:
            return res['Volumes'][0]
        return res['Volumes']

    def get_volume_state(self, volume_id):
        return self.describe_volume(volume_id)['VolumeStatus']

    def wait_for_target_state(self, volume_id, target_state, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            volume_state = self.get_volume_state(volume_id)
            ctx.logger.info('Waiting for volume "{0}" to be {1}. current state: {2}'
                            .format(volume_id, target_state, volume_state))
            if volume_state == target_state:
                return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting server to target state failed! the current "
                                  "state is {0}, the target state is {1}".format(volume_state, target_state))

    def update_runtime_properties(self, volume_id):
        volume_info = self.describe_volume(volume_id)
        volume = {
            'size': volume_info['Size'],
            'device_name': volume_info['Attachment'][0]['MountPoint'] if volume_info.get('Attachment') else None,
        }
        volume_info.pop('Size', None)
        volume.update(volume_info)
        ctx.instance.runtime_properties.update({
            'external_id': volume_info['VolumeId'],
            'external_name': volume_info['VolumeName'],
            'volume_type': volume_info['VolumeType'],
            'volume': volume
        })
        ctx.instance.update()

    def _create(self):
        params = self.prepare_params()
        ctx.logger.info("Volume creating params is {0}".format(params))
        return Helper().execute_request('ebs', 'create_volume', params)['VolumeId']

    def _is_create_system_disk(self):
        '''
        System_disk has been created when instance was created
        We Just need to update runtime_properties.
        '''
        if not convert2bool(ctx.node.properties['resource_config'].get('is_system_disk')):
            return False
        vm = self.get_related_vm()
        instance_id = vm.runtime_properties['external_id']
        ebs_system_disk_info = self.get_system_volume_by_ebs(instance_id)
        if ebs_system_disk_info:
            ctx.instance.runtime_properties['volume'] = {'size': ebs_system_disk_info.get('Size')}
            ctx.instance.runtime_properties['volume_type'] = ebs_system_disk_info.get('VolumeType')
            ctx.instance.runtime_properties['host_id'] = instance_id
            ctx.instance.runtime_properties['external_id'] = ebs_system_disk_info.get('VolumeId')
            ctx.instance.runtime_properties['external_name'] = ebs_system_disk_info.get('VolumeName')
            attachments = ebs_system_disk_info.get('Attachment', [])
            if attachments:
                ctx.instance.runtime_properties['volume']['device_name'] = attachments[0].get('MountPoint')
        else:  # from ebs or kec
            kec_system_disk_info = self.get_system_volume_by_kec(instance_id)
            if not kec_system_disk_info:
                ctx.logger.warn("Can not get system disk info!!!")
                return True
            external_name = kec_system_disk_info.get('LocalVolumeName')
            # ex: ksc-3190b895-66c9-456f-ab22-4cd92ac98cc6-vdc  -> /dev/vdc
            device_name = '/dev/' + external_name.split('-')[-1]
            ctx.instance.runtime_properties['volume'] = {'size': kec_system_disk_info.get('LocalVolumeSize'),
                                                         'device_name': device_name}
            ctx.instance.runtime_properties['volume_type'] = kec_system_disk_info.get('LocalVolumeType')
            ctx.instance.runtime_properties['host_id'] = instance_id
            ctx.instance.runtime_properties['external_id'] = kec_system_disk_info.get('LocalVolumeId')
            ctx.instance.runtime_properties['external_name'] = kec_system_disk_info.get('LocalVolumeName')
        return True

    def get_system_volume_by_kec(self, instance_id):
        request_body = {
            'InstanceId': instance_id,
        }
        volumes = Helper().execute_request('kec', 'describe_local_volumes', request_body).get('LocalVolumeSet', [])
        for volume in volumes:
            if volume.get("LocalVolumeCategory") == 'system':
                return volume

    def get_system_volume_by_ebs(self, instance_id):
        request_body = {
            'InstanceId': instance_id,
        }
        volumes = Helper().execute_request('ebs', 'describe_instance_volumes', request_body).get('Attachments', [])
        for volume in volumes:
            if volume['VolumeCategory'] == 'system':
                return volume

    def create(self):
        if self._is_create_system_disk():
            return
        if convert2bool(self.node_properties['use_external_resource']) is True:
            volume_id = validate_parameter('resource_id', self.resource_config)
        else:
            volume_id = self._create()
            self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_AVAILABLE)
            self.update_runtime_properties(volume_id)
        vm_instance = self.get_related_vm()
        if vm_instance:
            server_id = vm_instance.runtime_properties['external_id']
            server_instance_id = vm_instance.id
            self.attach(server_id, volume_id, server_instance_id)

    def _delete(self, volume_id):
        Helper().execute_request('ebs', 'delete_volume', {'VolumeId': volume_id})

    def delete(self):
        if ctx.node.properties['resource_config'].get('is_system_disk'):
            return
        volume_id = ctx.instance.runtime_properties['external_id']
        volume_state = self.get_volume_state(volume_id)
        vm_id = ctx.instance.runtime_properties.get('vm_id')
        if volume_state == constants.KS_VOLUME_STATE_IN_USE and vm_id:
            self.detach(vm_id, volume_id)
        volume_state = self.get_volume_state(volume_id)
        if volume_state not in (
            constants.KS_VOLUME_STATE_AVAILABLE,
            constants.KS_VOLUME_STATE_ERROR,
            constants.KS_VOLUME_STATE_RECYCLING,
        ):
            raise NonRecoverableError("The state of the volume that can be deleted is available/error/recycling,"
                                      "the volume {0} current state is {1}".format(volume_id, volume_state))
        self._delete(volume_id)
        ctx.instance.runtime_properties = {}

    def _attach(self, vm_id, volume_id):
        Helper().execute_request('ebs', 'attach_volume', {'VolumeId': volume_id, 'InstanceId': vm_id,
                                                          'DeleteWithInstance': True})

    def attach(self, server_id, volume_id, server_instance_id):
        volume_state = self.get_volume_state(volume_id)
        if volume_state != constants.KS_VOLUME_STATE_AVAILABLE:
            raise NonRecoverableError("The state of the volume that can be attached is available,"
                                      "the volume {0} current state is {1}".format(volume_id, volume_state))

        vm_state = Compute().get_vm_state(server_id)
        if vm_state not in (constants.KS_INSTANCE_STATE_ACTIVE, constants.KS_INSTANCE_STATE_STOPPED):
            raise NonRecoverableError("The state of the instance that can be attached is active or stopped,"
                                      "the instance {0} current state is {1}".format(server_id, vm_state))

        self._attach(server_id, volume_id)
        self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_IN_USE)
        self.update_runtime_properties(volume_id)
        self.write_vm_info(server_id)

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        self.attach(server_id, volume_id, server_id)

    def _detach(self, vm_id, volume_id):
        Helper().execute_request('ebs', 'detach_volume', {
            'VolumeId': volume_id,
            'InstanceId': vm_id})

    @staticmethod
    def _remove_vm_info():
        ctx.instance.runtime_properties.update({
            'host_id': None
        })
        ctx.instance.update()

    def detach(self, vm_id, volume_id):
        self._detach(vm_id, volume_id)
        self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_AVAILABLE)
        self.update_runtime_properties(volume_id)
        self._remove_vm_info()

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        vm_id = validate_parameter('server_id', kwargs)
        self.detach(vm_id, volume_id)

    def _resize(self, volume_id, size):
        Helper().execute_request('ebs', 'resize_volume', {'VolumeId': volume_id, 'Size': size})

    def resize(self, volume_id, size):

        volume_info = self.describe_volume(volume_id)
        volume_state = volume_info["VolumeStatus"]
        volume_category = volume_info["VolumeCategory"]
        volume_size = volume_info["Size"]
        if volume_category != "data":
            raise NonRecoverableError("The category of the volume that can be resized is data,"
                                      "the volume {0} current category is {1}".format(volume_id, volume_category))
        if size <= volume_size:
            raise NonRecoverableError("The resized size : {} of the volume: {} must bigger than the current size: {}".
                                      format(size, volume_id, volume_size))

        if volume_state != constants.KS_VOLUME_STATE_AVAILABLE:
            if volume_state == constants.KS_VOLUME_STATE_IN_USE:
                vm_id = volume_info.get("InstanceId")
                if not vm_id:
                    pass
                vm_state = Compute().describe_vm(vm_id)
                ctx.logger.info("Volume resize vm : {},status is {}".format(vm_id, vm_state))
                self._detach(vm_id, volume_id)
                self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_AVAILABLE)
                self._resize(volume_id, size)
                self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_AVAILABLE)
                time.sleep(2)  # 扩容成功到可以挂载存在偶发性时延
                self._attach(vm_id, volume_id)
                self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_IN_USE)
                vm_state = Compute().describe_vm(vm_id)
                ctx.logger.info("Volume resize END vm : {},status is {}".format(vm_id, vm_state))
            else:
                raise NonRecoverableError("The state of the volume that can be resized is available,"
                                          "the volume {0} current state is {1}".format(volume_id, volume_state))
        else:
            self._resize(volume_id, size)
            self.wait_for_target_state(volume_id, constants.KS_VOLUME_STATE_AVAILABLE)
        self.update_runtime_properties(volume_id)

    def custom_resize(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        size = self.validate_parameter_size(kwargs)
        self.resize(volume_id, size)

    def validate_parameter_size(self, kwargs):
        size = int(validate_parameter('size', kwargs))
        if size < 1 or size > 32000:
            raise NonRecoverableError("The range of the volume that can be resized is 1-32000 GB,"
                                      "the given size is {}".format(size))
        return size
