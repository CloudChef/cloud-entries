# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
from cloudify import ctx
from abstract_plugin.platforms.common.connector import Connector
from abstract_plugin.platforms.common import constants
from abstract_plugin.platforms.gcp.client import GCPConnect
from cloudify.exceptions import NonRecoverableError


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()
        self.project = self.connection_config.get('project_id')

    def get_client(self, api_name='compute', api_version='v1'):
        client = GCPConnect(self.connection_config, api_name, api_version).connection()
        return client

    @staticmethod
    def save_runtime_properties(resource_type, info=None, extra_values={}):
        if info:
            info_key = '_'.join([resource_type, 'info'])
            required_values = {
                constants.EXTERNAL_ID: info.get('name'),
                constants.EXTERNAL_NAME: info.get('name'),
                info_key: info
            }
            ctx.instance.runtime_properties.update(required_values)

        ctx.instance.runtime_properties.update(extra_values)
        ctx.instance.update()

    def _wait_for_operation(self, server, project, zone, operation, timeout=600, sleep_interval=10):
        ctx.logger.info('Waiting for operation to finish...')
        timeout = time.time() + timeout
        while time.time() < timeout:
            result = server.zoneOperations().get(
                project=project,
                zone=zone,
                operation=operation).execute()

            if result['status'] == 'DONE':
                print("done.")
                if 'error' in result:
                    raise Exception(result['error'])
                return result

            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting for operation to finish failed!")

    def describe_volume(self, compute, volume_id):
        try:
            res = compute.disks().get(
                project=self.project,
                zone=self.zone,
                disk=volume_id).execute()
            return res
        except Exception as e:
            raise NonRecoverableError("Failed to query information of volume {0}, "
                                      "the error message is {1}".format(volume_id, e))

    def describe_instance(self, compute, instance_id):
        try:
            res = compute.instances().get(
                project=self.project,
                zone=self.zone,
                instance=instance_id).execute()
            return res
        except Exception as e:
            raise NonRecoverableError("Failed to query information of instance {0}, "
                                      "the error message is {1}".format(instance_id, e))

    def get_vm_info(self, compute, instance_id):
        vm_info = self.describe_instance(compute, instance_id)
        networks = vm_info['networkInterfaces']
        vm_info['networks'] = networks
        return vm_info
