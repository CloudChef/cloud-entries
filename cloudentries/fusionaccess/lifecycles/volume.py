# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.volume import CommonVolume
from .base import Base
from .compute import Compute
from . import constants


class Volume(Base, CommonVolume):
    def __init__(self):
        super(Volume, self).__init__()
        self.action_mapper = {
            "attach_volume": self.custom_attach,
            "detach_volume": self.custom_detach,
            "resize_volume": self.custom_resize
        }
        self.conn = self.get_client()

    def create(self):
        if self._is_create_system_disk():
            return True
        create_ret = self._create()  # noqa
        volume_id = ""  # get volume_id from create_ret
        self.wait_for_target_status(volume_id, constants.VOLUME_STATE_AVAILABLE)
        self.update_runtime_properties(volume_id)
        return

    def _create(self):
        params = self.prepare_params()
        url = ""
        try:
            res = self.conn.common_request("put", url, params)
            # handle res and return volume_info only
            return res
        except Exception as e:
            raise NonRecoverableError("Failed to create volume, the error message is {}".format(e))

    def _is_create_system_disk(self):
        is_system_disk = self.resource_config.get('is_system_disk')
        if is_system_disk and str(is_system_disk).lower() == "true":
            vm_instance = self.get_related_vm()
            if vm_instance:
                server_id = vm_instance.runtime_properties['external_id']
                vm_info = Compute().describe_vm(server_id)  # noqa
                volume_id = ""  # get volume_id from vm_info
                self.update_runtime_properties(volume_id)
                return True
        return False

    def delete(self):
        pass

    def custom_attach(self):
        pass

    def custom_detach(self):
        pass

    def custom_resize(self):
        pass

    def update_runtime_properties(self, volume_id):
        volume_info = self.describe_volume(volume_id)
        volume = {
            'size': volume_info.get('size'),  # unit: GB
            'device_name': volume_info.get('device_name', ''),
        }
        volume.update(volume_info)
        ctx.instance.runtime_properties.update({
            'external_id': volume_info.get('disk_id'),
            'external_name': volume_info.get('disk_name'),
            'volume_type': volume_info.get('disk_type'),  # system | data
            'volume': volume
        })
        ctx.instance.update()

    def describe_volume(self, volume_id):
        params = {}
        url = ""
        try:
            res = self.conn.common_request("get", url, params)
            # handle res and return volume_info only
            return res
        except Exception as e:
            raise NonRecoverableError("Failed to describe volume: {}, the error message is {}".format(volume_id, e))

    def get_volume_status(self, volume_id):
        volume_info = self.describe_volume(volume_id)  # noqa
        volume_status = ""  # get volume_status from vm_info
        return volume_status

    def wait_for_target_status(self, volume_id, target_status, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            volume_state = self.get_volume_status(volume_id)
            ctx.logger.info('Waiting for server "{0}" to be {1}. current state: {2}'
                            .format(volume_id, target_status, volume_state))
            if volume_state == target_status:
                return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting volume to target state failed! the current "
                                  "state is {0}, the target state is {1}".format(volume_state, target_status))

    def prepare_params(self):
        # change key-value according to concrete cloud api
        params = {
            'name': self.resource_config.get('name') or ctx.instance.id,
            'size': self.resource_config.get('size')
        }
        return params
