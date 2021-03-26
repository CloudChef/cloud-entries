# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter, drop_none
from . import constants
from abstract_plugin.platforms.common.volume import CommonVolume
from .base import Base
from .compute import Compute


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }

    @staticmethod
    def write_vm_info(vm_id, server_instance_id):
        vm = Compute().describe_vm(vm_id)
        ctx.instance.runtime_properties.update({
            'vm_id': vm_id,
            'vm_info': vm,
            'host_id': server_instance_id
        })
        ctx.instance.update()

    def prepare_params(self):
        params = {
            'Region': self.connection_config['region'],
            'Zone': self.zone,
            'Name': self.resource_config.get('volume_name') or ctx.instance.id,
            'DiskType': self.resource_config.get('volume_type'),
            'Size': self.resource_config.get('size'),
            'ChargeType': self.resource_config.get('charge_type') or 'Dynamic',
            'PurchaseTime': self.resource_config.get('purchase_time') or 0
        }
        return drop_none(params)

    def describe_volume(self, volume_id):
        params = {
            'Action': 'DescribeUDisk',
            'Region': self.connection_config['region'],
            'UDiskId': volume_id
        }
        try:
            res = self.connection.get('/', params)
            return res['DataSet'][0]
        except KeyError:
            raise NonRecoverableError("Can not query the information of volume in ucloud.")
        except Exception as e:
            raise NonRecoverableError("Failed to query information of volume {0}, "
                                      "the error message is {1}".format(volume_id, e))

    def get_volume_state(self, volume_id):
        return self.describe_volume(volume_id)['Status']

    def wait_for_target_state(self, volume_id, target_state, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            volume_state = self.get_volume_state(volume_id)
            ctx.logger.info('Waiting for server "{0}" to be {1}. current state: {2}'
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
            'device_name': volume_info['DeviceName'] if volume_info.get('DeviceName') else None,
        }
        volume_info.pop('Size', None)
        volume.update(volume_info)
        ctx.instance.runtime_properties.update({
            'external_id': volume_info['UDiskId'],
            'external_name': volume_info['Name'],
            'volume_type': volume_info['DiskType'],
            'volume': volume
        })
        ctx.instance.update()

    def _create(self):
        params = self.prepare_params()
        params['Action'] = 'CreateUDisk'
        ctx.logger.info("Volume creating params is {0}".format(params))
        resp = self.connection.get('/', params)
        if resp.get('RetCode'):
            raise NonRecoverableError("Create volume failed! the params is {0},"
                                      "the error message is {1}".format(params, resp.get('Message')))
        try:
            return resp['UDiskId'][0]
        except Exception as e:
            raise NonRecoverableError("Create volume failed! the params is {0},"
                                      "the error message is {1}".format(params, e))

    def create(self):
        if self.use_external_resource is True:
            volume_id = validate_parameter('resource_id', self.resource_config)
        else:
            if self._is_system_disk():
                return
            volume_id = self._create()
            self.wait_for_target_state(volume_id, constants.UC_VOLUME_STATE_AVAILABLE)
            self.update_runtime_properties(volume_id)
        vm_instance = self.get_related_vm()
        if vm_instance:
            server_id = vm_instance.runtime_properties['external_id']
            server_instance_id = vm_instance.id
            self.attach(server_id, volume_id, server_instance_id)

    def _is_system_disk(self):
        is_system_disk = self.resource_config.get('is_system_disk')
        if is_system_disk and str(is_system_disk).lower() == "true":
            vm_instance = self.get_related_vm()
            if vm_instance:
                server_id = vm_instance.runtime_properties['external_id']
                vm_info = Compute().describe_vm(server_id)
                disk_info = vm_info.get('DiskSet')
                for disk in disk_info:
                    if disk['IsBoot']:
                        volume_id = disk['DiskId']
                        self.update_runtime_properties(volume_id)
                    return True
        return False

    def _delete(self, volume_id):
        params = {
            'Action': 'DeleteUDisk',
            'Region': self.connection_config['region'],
            'Zone': self.zone,
            'UDiskId': volume_id
        }
        try:
            resp = self.connection.get('/', params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Delete volume failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            ctx.logger.info("Delete volume failed! the params is {0},"
                            "the error message is {1}".format(params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Delete volume {0} failed, the error message is {1}".format(volume_id, e))

    def delete(self):
        volume_id = ctx.instance.runtime_properties['external_id']
        volume_state = self.get_volume_state(volume_id)
        vm_id = ctx.instance.runtime_properties.get('vm_id')
        if volume_state == 'InUse' and vm_id:
            self.detach(vm_id, volume_id)
        volume_state = self.get_volume_state(volume_id)
        if volume_state not in (
                constants.UC_VOLUME_STATE_AVAILABLE,
                constants.UC_VOLUME_STATE_FAILED,
                constants.UC_VOLUME_STATE_RESTORING,
        ):
            raise NonRecoverableError("The state of the volume that can be deleted is available/error/recycling,"
                                      "the volume {0} current state is {1}".format(volume_id, volume_state))
        self._delete(volume_id)
        ctx.instance.runtime_properties = {}

    def _attach(self, vm_id, volume_id):
        params = {
            'Action': 'AttachUDisk',
            'Region': self.connection_config['region'],
            'Zone': self.zone,
            'UDiskId': volume_id,
            'UHostId': vm_id
        }
        try:
            resp = self.connection.get('/', params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Attach volume failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            ctx.logger.info("Attach volume failed! the params is {0},"
                            "the error message is {1}".format(params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Attach volume {0} to server {1} failed, "
                                      "the error message is {2}".format(volume_id, vm_id, e))

    def attach(self, server_id, volume_id, server_instance_id):
        self._attach(server_id, volume_id)
        self.wait_for_target_state(volume_id, constants.UC_VOLUME_STATE_IN_USE)
        self.update_runtime_properties(volume_id)
        self.write_vm_info(server_id, server_instance_id)

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        server_instance_id = validate_parameter('server_instance_id', kwargs)
        self.attach(server_id, volume_id, server_instance_id)

    def _detach(self, vm_id, volume_id):
        params = {
            'Action': 'DetachUDisk',
            'Region': self.connection_config['region'],
            'Zone': self.zone,
            'UDiskId': volume_id,
            'UHostId': vm_id
        }
        try:
            resp = self.connection.get('/', params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Detach volume failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            ctx.logger.info("Detach volume failed! the params is {0},"
                            "the error message is {1}".format(params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Detach volume {0} to server {1} failed,"
                                      "the error message is {2}".format(volume_id, vm_id, e))

    @staticmethod
    def _remove_vm_info():
        ctx.instance.runtime_properties.update({
            'vm_id': None,
            'vm_info': None,
            'host_id': None
        })
        ctx.instance.update()

    def detach(self, vm_id, volume_id):
        self._detach(vm_id, volume_id)
        self.wait_for_target_state(volume_id, constants.UC_VOLUME_STATE_AVAILABLE)
        self.update_runtime_properties(volume_id)
        self._remove_vm_info()

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        vm_id = validate_parameter('server_id', kwargs)
        self.detach(vm_id, volume_id)

    def _resize(self, zone, volume_id, size):
        params = {
            'Action': 'ResizeUDisk',
            'Region': self.connection_config['region'],
            'Zone': zone,
            'UDiskId': volume_id,
            'Size': size
        }
        try:
            resp = self.connection.get('/', params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Resize volume failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            ctx.logger.info("Resize volume failed! the params is {0},"
                            "the error message is {1}".format(params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Resize volume {0} failed! the error message is {1}".format(volume_id, e))

    def resize(self, volume_id, size):
        volume_state = self.get_volume_state(volume_id)
        if volume_state != constants.UC_VOLUME_STATE_AVAILABLE:
            raise NonRecoverableError("The state of the volume that can be resized is available,"
                                      "the volume {0} current state is {1}".format(volume_id, volume_state))
        zone = self.describe_volume(volume_id)['Zone']
        self._resize(zone, volume_id, size)
        self.update_runtime_properties(volume_id)

    def custom_resize(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        size = validate_parameter('size', kwargs)
        self.resize(volume_id, size)
