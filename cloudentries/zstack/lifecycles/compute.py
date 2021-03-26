# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import copy
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password
from abstract_plugin.platforms.common.utils import validate_parameter
from . import constants
from .connection import Base
from abstract_plugin.platforms.common.compute import CommonCompute


class Compute(Base, CommonCompute):
    def __init__(self):
        super(Compute, self).__init__()
        self.vm_endpoint = '/vm-instances'

    def prepare_params(self):
        instance_name = self.resource_config.get('instance_name')
        hostname = None
        if not instance_name:
            instance_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or instance_name

        system_tags = ["consolePassword::{0}".format(
            decrypt_password(validate_parameter('password', self.resource_config)))]
        if self.get_ip():
            system_tags.append("staticIp::{0}::{1}".format(self.get_subnet(), self.get_ip()))

        params_info = {
            "name": instance_name,
            "instanceOfferingUuid": validate_parameter('flavor', self.resource_config),
            "imageUuid": validate_parameter('image_id', self.resource_config),
            "l3NetworkUuids": self.get_subnets(),
            "strategy": "InstantStart",
            "systemTags": system_tags
        }
        return params_info

    def describe_vm(self, instance_id):
        try:
            condition = {
                'resource_id': instance_id
            }
            res = self.client.call('get', self.vm_endpoint, condition=condition).json()
            return res['inventories'][0]
        except IndexError:
            return False
        except Exception as e:
            raise NonRecoverableError("Failed to query virtual machine information, "
                                      "the vm id {0}, the error message is {1}".format(instance_id, e))

    def get_vm_state(self, instance_id):
        vm_info = self.describe_vm(instance_id)
        if not vm_info:
            raise NonRecoverableError("Can not query the information of vm in zstack")
        return vm_info['state']

    def update_runtime_properties(self, instance_id):
        vm = self.describe_vm(instance_id)
        ctx.instance.runtime_properties.update({
            'external_id': vm['uuid'],
            'external_name': vm['name'],
            'vm_info': vm})
        self.set_ip_info(instance_id)
        ctx.instance.update()

    def set_ip_info(self, instance_id):
        ips = []
        networks = {}
        vm = self.describe_vm(instance_id)
        for index, vm_nic in enumerate(vm['vmNics']):
            vm_nic['name'] = 'network' + str(index)
            if len(vm_nic['usedIps']) > 0:
                vm_nic['ip'] = vm_nic['usedIps'][0].get('ip')
            networks['network' + str(index)] = vm_nic
            ips.append(vm_nic.get('ip'))
        ctx.instance.runtime_properties['network'] = networks
        ctx.instance.runtime_properties['ips'] = ips
        ctx.instance.runtime_properties['ip'] = ips[0] if ips else ''
        network_info = networks.get('network0')
        if self.use_external_resource:
            # There is not network connected to instance,instance is external.
            ctx.instance.runtime_properties['networks'] = {'Network': network_info}
        else:
            # Create by CMP.
            related_network = self.get_primary_network()
            networks_runtime = ctx.instance.runtime_properties.get('networks')
            networks_runtime[related_network.node.id].update(network_info)

    def _create(self):
        data = {
            "params": self.prepare_params()
        }
        output = copy.deepcopy(data)
        output['params']['systemTags'] = ["consolePassword::******"]
        ctx.logger.info("VM creating params is {0}".format(output))
        try:
            resp = self.client.call('post', body=data, endpoint=self.vm_endpoint).json()
            return resp['inventory']['uuid']
        except Exception as e:
            raise NonRecoverableError("Create vm failed! the params is {0}, "
                                      "the error message is {1}".format(output, e))

    def create(self):
        if self.use_external_resource is True:
            instance_id = validate_parameter('resource_id', self.node_properties)
        else:
            instance_id = self._create()
        self.update_runtime_properties(instance_id)

    def _start(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.ZSTACK_INSTANCE_STATE_RUNNING:
            ctx.logger.info("The virtual machine is active, No need to start!")
            return

        try:
            data = {
                "startVmInstance": {},
                "systemTags": [],
                "userTags": []
            }
            condition = {
                "resource_id": instance_id
            }
            self.client.call('put', endpoint=self.vm_endpoint, body=data, condition=condition,
                             rpc=True)
        except Exception as e:
            raise NonRecoverableError("Start instance {0} failed! the error message is {1}".format(
                instance_id, e))

    def start(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._start(instance_id)
        self.update_runtime_properties(instance_id)

    def _stop(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.ZSTACK_INSTANCE_STATE_STOPPED:
            ctx.logger.info("The virtual machine is stopped, No need to stop!")
            return
        try:
            data = {
                "stopVmInstance": {},
                "systemTags": [],
                "userTags": []
            }
            condition = {
                "resource_id": instance_id
            }
            self.client.call('put', endpoint=self.vm_endpoint, body=data, condition=condition,
                             rpc=True)
        except Exception as e:
            raise NonRecoverableError("Stop instance {0} failed! the stop params is {1}, "
                                      "the error message is {2}".format(instance_id, data, e))

    def stop(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        if not self.describe_vm(instance_id):
            ctx.logger.info("The virtual machine is not exist, No need to stop!")
            return
        self._stop(instance_id)
        self.update_runtime_properties(instance_id)

    def _reboot(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.ZSTACK_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Can not reboot virtual machine which state is stopped, you can start it!")
        try:
            data = {
                "rebootVmInstance": {},
                "systemTags": [],
                "userTags": []
            }
            condition = {
                "resource_id": instance_id
            }
            self.client.call('put', endpoint=self.vm_endpoint, body=data, condition=condition,
                             rpc=True)
        except Exception as e:
            raise NonRecoverableError("Stop instance {0} failed! the start params is {1}, "
                                      "the error message is {2}".format(instance_id, data, e))

    def reboot(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._reboot(instance_id)
        self.update_runtime_properties(instance_id)

    def delete(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        if not self.describe_vm(instance_id):
            ctx.logger.info("The virtual machine is not exist, No need to delete!")
            return
        try:
            condition = {
                "resource_id": instance_id
            }
            self.client.call('delete', endpoint=self.vm_endpoint, condition=condition)
        except Exception as e:
            raise NonRecoverableError("Delete vm {0} failed, the error message is {1}".format(
                instance_id, e))
        self.release_ip_in_delete_operation()
