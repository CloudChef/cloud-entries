# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
import base64

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password, convert2bool
from abstract_plugin.platforms.common.utils import validate_parameter
from abstract_plugin.platforms.common.compute import CommonCompute
from .base import Base
from . import constants


class Compute(Base, CommonCompute):
    def __init__(self):
        super(Compute, self).__init__()

    def get_size(self, image_id):
        params = {
            'Region': self.connection_config['region'],
            'Action': 'DescribeImage',
            'ImageId': image_id
        }
        resp = self.get_client().get('/', params)
        try:
            if resp.get('RetCode'):
                raise NonRecoverableError("Get volume size failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            return resp['ImageSet'][0]['ImageSize']
        except Exception as e:
            raise NonRecoverableError("Failed to query image size, "
                                      "the image id {0}, the error message is {1}".format(image_id, e))

    def prepare_params(self):
        zone = self.resource_config['available_zone_id']
        password = decrypt_password(validate_parameter('password', self.resource_config))

        instance_name = self.resource_config.get('instance_name')
        hostname = None
        if not instance_name:
            instance_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or instance_name

        image_id = validate_parameter('image_id', self.resource_config)
        params_info = {
            'Region': self.resource_config.get('region'),
            'Zone': zone,
            'ImageId': image_id,
            'SubnetId': self.get_subnet(),
            'Password': base64.b64encode(password.encode('utf-8')).decode('utf-8'),
            'Name': instance_name,
            'ChargeType': self.resource_config.get('charge_type') or 'Dynamic',
            'LoginMode': self.resource_config.get('login_mode') or 'Password',
            'Disks.0.IsBoot': 'True',
            'Disks.0.Type': constants.UC_VOLUME_TYPE,
            'Disks.0.Size': self.get_size(image_id),
            'MachineType': constants.MachineType,
            'CPU': self.resource_config['cpus'],
            'Memory': self.resource_config['memory']
        }

        return params_info

    def describe_vm(self, instance_id):
        params = {
            'Region': self.connection_config['region'],
            'Action': 'DescribeUHostInstance',
            'UHostIds': instance_id
        }
        try:
            resp = self.get_client().get('/', params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Create volume failed! the params is {0},"
                                          "the error message is {1}".format(params, resp.get('Message')))
            return resp['UHostSet'][0]
        except IndexError:
            return False
        except Exception as e:
            raise NonRecoverableError("Failed to query virtual machine information, "
                                      "the vm id {0}, the error message is {1}".format(instance_id, e))

    def get_vm_state(self, instance_id):
        vm_info = self.describe_vm(instance_id)
        if not vm_info:
            raise NonRecoverableError("Can not query the information of vm in ucloud")
        return vm_info['State']

    def wait_for_target_state(self, instance_id, target_state, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            instance_state = self.get_vm_state(instance_id)
            ctx.logger.info('Waiting for server "{0}" to be {1}. current state: {2}'
                            .format(instance_id, target_state, instance_state))
            if isinstance(target_state, tuple):
                if instance_state in target_state:
                    return
            else:
                if instance_state == target_state:
                    return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting server to target state failed! the current "
                                  "state is {0}, the target state is {1}".format(instance_state, target_state))

    def update_runtime_properties(self, instance_id):
        vm = self.describe_vm(instance_id)
        ctx.instance.runtime_properties.update({
            'external_id': vm['UHostId'],
            'external_name': vm['Name'],
            'ip': vm['IPSet'][0]['IP'],
            'vm_info': vm})
        self.set_ip_info(instance_id)
        ctx.instance.update()

    def set_ip_info(self, instance_id):
        ips = []
        vm = self.describe_vm(instance_id)
        networks = {}
        for index, ip_set in enumerate(vm['IPSet']):
            ips.append(ip_set['IP'])
            ip_set['ip'] = ip_set['IP']
            ip_set['name'] = 'network' + str(index)
            networks['network' + str(index)] = ip_set
        ctx.instance.runtime_properties['networks'] = networks
        ctx.instance.runtime_properties['ips'] = ips

    def _create(self):
        params = self.prepare_params()
        params['Action'] = 'CreateUHostInstance'
        ctx.logger.info("VM creating params is {0}".format(params))
        resp = self.get_client().get('/', params)
        if resp.get('RetCode'):
            raise NonRecoverableError("Create vm failed! the params is {0}, "
                                      "the error message is {1}".format(params, resp.get('Message')))
        ctx.logger.info("Create vm failed! the params is {0},"
                        "the error message is {1}".format(params, resp.get('Message')))
        try:
            return resp['UHostIds'][0]
        except Exception as e:
            raise NonRecoverableError("Create vm failed! the params is {0}, "
                                      "the error message is {1}".format(params, e))

    def create(self):
        if convert2bool(self.resource_config.get('use_external_resource')) is True:
            instance_id = validate_parameter('resource_id', self.resource_config)
        else:
            instance_id = self._create()
            self.wait_for_target_state(instance_id, constants.UC_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)

    def _start(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.UC_INSTANCE_STATE_ACTIVE:
            ctx.logger.info("The virtual machine is active, No need to start!")
            return
        if vm_state != constants.UC_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Only virtual machines that are in a stopped state can be started")
        else:
            params = {
                'Region': self.connection_config['region'],
                'Action': 'StartUHostInstance',
                'UHostId': instance_id
            }
            try:
                resp = self.connection.get('/', params)
                if resp.get('RetCode'):
                    raise NonRecoverableError("Start volume failed! the params is {0},"
                                              "the error message is {1}".format(params, resp.get('Message')))
                ctx.logger.info("Start volume failed! the params is {0},"
                                "the error message is {1}".format(params, resp.get('Message')))
            except Exception as e:
                raise NonRecoverableError("Start instance {0} failed! the error message is {1}".format(
                    instance_id, e))

    def start(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._start(instance_id)
        self.wait_for_target_state(instance_id, constants.UC_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)

    def _stop(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.UC_INSTANCE_STATE_STOPPED:
            ctx.logger.info("The virtual machine is stopped, No need to stop!")
            return
        stop_params = {
            "Action": "StopUHostInstance",
            "UHostId": instance_id,
            "Region": self.connection_config['region']}
        try:
            resp = self.connection.get('/', stop_params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Stop volume failed! the params is {0},"
                                          "the error message is {1}".format(stop_params, resp.get('Message')))
            ctx.logger.info("Stop volume failed! the params is {0},"
                            "the error message is {1}".format(stop_params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Stop instance {0} failed! the stop params is {1}, "
                                      "the error message is {2}".format(instance_id, stop_params, e))

    def stop(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        if not self.describe_vm(instance_id):
            ctx.logger.info("The virtual machine is not exist, No need to stop!")
            return
        self._stop(instance_id)
        self.wait_for_target_state(instance_id, constants.UC_INSTANCE_STATE_STOPPED)
        self.update_runtime_properties(instance_id)

    def _reboot(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == constants.UC_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Can not reboot virtual machine which state is stopped, you can start it!")
        reboot_params = {
            "Action": "RebootUHostInstance",
            'UHostId': instance_id,
            "Region": self.connection_config['region']}
        try:
            resp = self.get_client().get('/', reboot_params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Reboot volume failed! the params is {0},"
                                          "the error message is {1}".format(reboot_params, resp.get('Message')))
            ctx.logger.info("Reboot volume failed! the params is {0},"
                            "the error message is {1}".format(reboot_params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Reboot vm {0} failed! the reboot params is {1}, the error message is {2}".format(
                instance_id, reboot_params, e))

    def reboot(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._reboot(instance_id)
        self.wait_for_target_state(instance_id, constants.UC_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)

    def delete(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        if not self.describe_vm(instance_id):
            ctx.logger.info("The virtual machine is not exist, No need to delete!")
            return
        vm_state = self.get_vm_state(instance_id)
        if vm_state != constants.UC_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Can not delete virtual machine which state isn't stopped, you need stop it!")
        delete_params = {
            "Action": "TerminateUHostInstance",
            "UHostId": instance_id,
            "Region": self.connection_config['region']
        }
        try:
            resp = self.connection.get('/', delete_params)
            if resp.get('RetCode'):
                raise NonRecoverableError("Delete volume failed! the params is {0},"
                                          "the error message is {1}".format(delete_params, resp.get('Message')))
            ctx.logger.info("Delete volume failed! the params is {0},"
                            "the error message is {1}".format(delete_params, resp.get('Message')))
        except Exception as e:
            raise NonRecoverableError("Delete vm {0} failed, the error message is {1}".format(
                instance_id, e))
        self.release_ip_in_delete_operation()
