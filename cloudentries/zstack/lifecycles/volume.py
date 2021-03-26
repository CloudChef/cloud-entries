# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter
from abstract_plugin.platforms.common.volume import CommonVolume
from .connection import Base
from .compute import Compute


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }
        self.volume_endpoint = '/volumes'
        self.create_volume_endpoint = self.volume_endpoint + '/data'

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
            'name': self.resource_config.get('volume_name') or ctx.instance.id,
            'diskOfferingUuid': validate_parameter('volume_type', self.resource_config),
        }
        return params

    def describe_volume(self, volume_id):
        try:
            condition = {
                'resource_id': volume_id
            }
            res = self.client.call('get', self.volume_endpoint, condition=condition).json()
            return res['inventories'][0]
        except KeyError:
            raise NonRecoverableError("Can not query the information of volume in ksyun.")
        except Exception as e:
            raise NonRecoverableError("Failed to query information of volume {0}, "
                                      "the error message is {1}".format(volume_id, e))

    def get_volume_state(self, volume_id):
        return self.describe_volume(volume_id)['state']

    def write_runtime(self, volume_id):
        volume_info = self.describe_volume(volume_id)
        volume = {
            'size': volume_info['size'] / 1024 / 1024 / 1024,
            'device_name': None,
            'volume_type': None,
        }
        volume_info.update(volume)
        ctx.instance.runtime_properties.update({
            'external_id': volume_info['uuid'],
            'external_name': volume_info['name'],
            'volume': volume_info,
            'size': volume_info['size'] / 1024 / 1024 / 1024,
            'device_name': None,
            'volume_type': 'Could Disk',
        })
        ctx.instance.update()

    def _create(self):
        params = self.prepare_params()
        ctx.logger.info("Volume creating params is {0}".format(params))
        try:
            data = {
                'params': self.prepare_params()
            }
            resp = self.client.call('post', self.create_volume_endpoint, body=data).json()
            return resp['inventory']['uuid']
        except Exception as e:
            raise NonRecoverableError("Create volume failed! the params is {0},"
                                      "the error message is {1}".format(params, e))

    def create(self):
        if self.use_external_resource is True:
            volume_id = validate_parameter('resource_id', self.resource_config)
        else:
            volume_id = self._create()
            self.write_runtime(volume_id)
        vm_instance = self.get_related_vm()
        if vm_instance:
            server_id = vm_instance.runtime_properties['external_id']
            server_instance_id = vm_instance.id
            self.attach(server_id, volume_id, server_instance_id)

    def _delete(self, volume_id):
        try:
            condition = {
                'resource_id': volume_id
            }
            self.client.call('delete', self.volume_endpoint, condition=condition)
        except Exception as e:
            raise NonRecoverableError("Delete volume {0} failed, the error message is {1}".format(volume_id, e))

    def delete(self):
        volume_id = ctx.instance.runtime_properties['external_id']
        self._delete(volume_id)
        ctx.instance.runtime_properties = {}

    def _attach(self, vm_id, volume_id):
        try:
            attach_url = '/volumes/{volume_id}/vm-instances/{vm_id}'.format(volume_id=volume_id, vm_id=vm_id)
            self.client.call('post', attach_url)
        except Exception as e:
            raise NonRecoverableError("Attach volume {0} to server {1} failed, "
                                      "the error message is {2}".format(volume_id, vm_id, e))

    def attach(self, server_id, volume_id, server_instance_id):
        self._attach(server_id, volume_id)
        self.write_runtime(volume_id)
        self.write_vm_info(server_id, server_instance_id)

    def custom_attach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        server_id = validate_parameter('server_id', kwargs)
        server_instance_id = validate_parameter('server_instance_id', kwargs)
        self.attach(server_id, volume_id, server_instance_id)

    def _detach(self, vm_id, volume_id):
        try:
            delete_url = '/volumes/{volume_id}/vm-instances?vmUuid={vm_id}'.format(volume_id=volume_id, vm_id=vm_id)
            self.client.call('delete', delete_url)
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
        self.write_runtime(volume_id)
        self._remove_vm_info()

    def custom_detach(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        vm_id = validate_parameter('server_id', kwargs)
        self.detach(vm_id, volume_id)

    def _resize(self, volume_id, size):
        try:
            resize_url = "/volumes/data/resize/{volume_id}/actions".format(volume_id=volume_id)
            data = {
                "resizeDataVolume": {
                    "size": size
                }
            }
            self.client.call('put', resize_url, body=data)
        except Exception as e:
            raise NonRecoverableError("Resize volume {0} failed! the error message is {1}".format(volume_id, e))

    def resize(self, volume_id, size):
        self._resize(volume_id, size)
        self.write_runtime(volume_id)

    def custom_resize(self, **kwargs):
        volume_id = ctx.instance.runtime_properties['external_id']
        size = validate_parameter('size', kwargs)
        size = int(size) * 1024 * 1024 * 1024
        self.resize(volume_id, size)
