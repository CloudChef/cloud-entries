# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
import time

from abstract_plugin.platforms.common.compute import CommonCompute
from abstract_plugin.platforms.fusioncompute.base import Base
from abstract_plugin.platforms.common import constants as common_constants
from abstract_plugin.platforms.common.utils import (
    validate_parameter,
    clear_runtime_properties
)
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from cloudify.utils import decrypt_password, convert2bool
from . import constants as fc_constants


class Compute(Base, CommonCompute):

    def __init__(self):
        super(Compute, self).__init__()
        self.fc_client = self.get_client()
        self.action_mapper = {
            "resize": self.resize,
            "modify_display_name": self.modify_display_name,
        }

    def _get_nics_params(self):
        nics = []
        networks = self.get_networks()
        for netwrok in networks:
            nic_info = self._get_nic_params(netwrok)
            nics.append(nic_info)

        return nics

    def _get_nic_params(self, network):
        network_info, subnet_info = self._get_network_info(network)
        subnet_id = subnet_info['urn']

        nic = {
            "portGroupUrn": subnet_id,
            "enableSecurityGroup": False,
            "securityGroupId": "",
        }

        return nic

    @staticmethod
    def _get_network_info(network):
        rp_props = network.instance.runtime_properties
        return rp_props.get('network_info'), rp_props.get('subnet_info')

    def _prepare_vm_config(self, image_id, disk_name):
        vcpu = validate_parameter('CPU', self.resource_config, not_empty=True)
        memory = validate_parameter('Memory', self.resource_config, not_empty=True)
        volume, datastore_urn = self.get_template_size_and_datastore(image_id)
        nics = self._get_nics_params()

        vm_config = {
            "cpu": {
                "quantity": vcpu,
            },
            "memory": {
                "quantityMB": memory,
            },
            "disks": [
                {
                    "diskName": disk_name,
                    "systemVolume": True,
                    "sequenceNum": 1,
                    "isDataCopy": True,
                    "quantityGB": volume,
                    "isThin": True,
                    "datastoreUrn": datastore_urn,
                }
            ],
            "nics": nics,
        }

        return vm_config

    def _prepare_request_params(self):
        default_vm_name, default_hostname = self.get_instance_names()
        vm_name = self.resource_config.get('instance_name', default_vm_name)
        if not vm_name:
            vm_name = ctx.instance.id
        image_id = validate_parameter('image_id', self.resource_config, not_empty=True)
        os_type = self.get_os_type(image_id)
        hostname = self.resource_config.get('hostname') or default_hostname or vm_name.replace('_', '-')
        if len(hostname) > 15:
            hostname = vm_name.replace('Compute_', '-')
        password = decrypt_password(self.resource_config.get('password'))
        disk_name = vm_name + '-OS-Disk'
        description = self.resource_config.get('description', '')
        location = self.zone
        is_binding_host = convert2bool(self.resource_config.get('is_binding_host', False))
        vm_config = self._prepare_vm_config(image_id, disk_name)

        data = {
            "name": vm_name,
            "description": description,
            "location": location,
            "isBindingHost": is_binding_host,
            "vmConfig": vm_config,
            "autoBoot": False,
            "isTemplate": False,
            "vmCustomization": {
                "osType": os_type,
                "hostname": hostname,
                "password": password,
                "workgroup": "workgroup",
            },
        }
        network_info = self.get_network_info()
        if network_info:
            ctx.logger.info("Using network_info {0}.".format(network_info))
            data['vmCustomization']['nicSpecification'] = [
                {"sequenceNum": 1,
                 "ip": network_info['ip'],
                 "cidr": network_info['cidr'],
                 "gateway": network_info['gateway'],
                 "netmask": network_info['netmask']
                 }
            ]
            dns_server = network_info.get('dns_servers', [])
            if dns_server:
                back_dns = dns_server[1] if len(dns_server) > 1 else dns_server[0]
                data['vmCustomization']['nicSpecification'][0].update({'setdns': dns_server[0], 'adddns': back_dns})

        return data

    def _create_external_instance(self):
        if not self.use_external_resource:
            return False

        ctx.logger.info('Create an existed FusionComputer VM: {}'.format(self.resource_id))
        instance_info = self.fc_client.servers.get(self.resource_id)
        ctx.logger.info('FusionComputer VM, prepare instance_info: {}'.format(instance_info))

        self.update_runtime_properties('compute', instance_info)
        nic_info = instance_info['vmConfig']['nics']
        self.update_network(nic_info)
        return True

    def create(self, *kwargs):
        if self._create_external_instance():
            return

        ctx.logger.info(
            'Creating instance by params: {}'.format(
                json.dumps(self.resource_config, indent=2)))

        image_id = validate_parameter('image_id', self.resource_config, not_empty=True)
        data = self._prepare_request_params()
        ctx.logger.info(
            'Creating instance of FusionCompute: {}, the image id:'.format(
                json.dumps(data, indent=2)))

        try:
            result = self.fc_client.servers.clone(image_id, data)
        except Exception as e:
            raise NonRecoverableError("Create instance failed, image id is {0}, "
                                      "data is {1}. the error is {2}".format(image_id, data, e))
        instance_id = result.get('urn')

        self.wait_for_target_state(instance_id, fc_constants.FC_INSTANCE_STATE_STOPPED)
        instance_info = self.fc_client.servers.get(instance_id)
        ctx.logger.info('FusionComputer VM, created instance_info: {}'.format(instance_info))

        extra_values = {
            common_constants.EXTERNAL_HOSTNAME: data['vmCustomization']['hostname'],
            'ip': instance_info['vmConfig']['nics'][0]['ip']
        }
        self.update_runtime_properties('compute', instance_info, extra_values)
        ctx.logger.info(
            'The instance was created successfully. result:{}'.format(
                json.dumps(result, indent=2)))

    def get_os_type(self, image_id):
        image_info = self.fc_client.servers.get(image_id)
        return image_info['osOptions']['osType']

    def get_template_size_and_datastore(self, image_id):
        image_info = self.fc_client.servers.get(image_id)
        volume_info = image_info['vmConfig']['disks'][0]
        datastore_urn = volume_info['datastoreUrn']
        volume = volume_info['quantityGB']
        return volume, datastore_urn

    def get_instance_state(self, instance_id):
        res = self.fc_client.servers.get(instance_id)
        if res:
            return res['status']
        else:
            raise NonRecoverableError('The virtual machine does not exist.')

    def wait_for_target_state(self, instance_id, target_state, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            instance_state = self.get_instance_state(instance_id)
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

    def wait_for_ip_generation(self, instance_id, timeout=600, sleep_interval=10, multi_check=3):
        timeout = time.time() + timeout
        check = 0
        while time.time() < timeout:
            instance_info = self.fc_client.servers.get(instance_id)
            ip_address = instance_info['vmConfig']['nics'][0]['ip']
            ctx.logger.debug('Waiting for IP generation...')
            if ip_address != '0.0.0.0':
                check += 1
            # There are two (system) steps to assigning IP in FusionCompute, and the IP may be different
            if check == multi_check:
                return
            time.sleep(sleep_interval)
        ctx.logger.debug('IP generation failed, please check your port configuration.')

    def update_network(self, nic_info):
        ip_address = nic_info[0]['ip']

        if self.use_external_resource:  # use external
            ctx.instance.runtime_properties["ip"] = ip_address
            ctx.instance.runtime_properties['networks'] = {"Network": nic_info}
        else:  # create CMP
            runtime_networks = ctx.instance.runtime_properties.get('networks')
            networks = self.get_networks()
            for network in networks:
                subnet_info = network.instance.runtime_properties['subnet_info']
                subnet_info['ip'] = ip_address
                network_node_id = network.node.id
                if runtime_networks:
                    if not runtime_networks.get(network_node_id):
                        runtime_networks[network_node_id] = {}
                    runtime_networks[network_node_id].update(subnet_info)
                else:
                    runtime_networks = {network_node_id: subnet_info}
            ctx.instance.runtime_properties.update(dict(networks=runtime_networks))
        ips = []
        for nic in nic_info:
            ips.append(nic.get('ip'))
        ctx.instance.runtime_properties['ips'] = ips
        ctx.instance.update()

    def start(self):
        instance_id = ctx.instance.runtime_properties[common_constants.EXTERNAL_ID]
        instance_state = self.get_instance_state(instance_id)

        if instance_state == fc_constants.FC_INSTANCE_STATE_ACTIVE:
            ctx.logger.info('The virtual machine is already on. It does not need to be started.')
            return
        elif instance_state == fc_constants.FC_INSTANCE_STATE_STOPPED:
            try:
                ctx.logger.info('Starting FusionCompute VM {}.'.format(instance_id))
                self.fc_client.servers.start(instance_id)
                self.wait_for_target_state(instance_id, fc_constants.FC_INSTANCE_STATE_ACTIVE)
                self.wait_for_ip_generation(instance_id)
                instance_info = self.fc_client.servers.get(instance_id)
                nic_info = instance_info['vmConfig']['nics']
                ip_address = nic_info[0]['ip']
                extra_values = {
                    'ip': ip_address
                }
                ctx.instance.runtime_properties.update(extra_values)
                self.update_network(nic_info)
            except Exception as e:
                raise NonRecoverableError("Start instance {0} failed! The error message is {1}".format(
                    instance_id, e))
        else:
            raise NonRecoverableError(
                'Only when the virtual machine is stopped can it be started.')

    def stop(self):
        instance_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        if not instance_id:
            ctx.logger.info('The virtual machine does not exist, skip the stop.')
            return
        if not self.get_vm(instance_id):
            ctx.logger.info('The virtual machine does not exist, skip the stop.')
            return

        instance_state = self.get_instance_state(instance_id)

        if instance_state == fc_constants.FC_INSTANCE_STATE_STOPPED:
            ctx.logger.info('The virtual machine has been turned off. It does not need to be shut down.')
            return
        elif instance_state == fc_constants.FC_INSTANCE_STATE_ACTIVE:
            try:
                ctx.logger.info('Stopping FusionCompute VM {}.'.format(instance_id))
                self.fc_client.servers.stop(instance_id)
                self.wait_for_target_state(instance_id, fc_constants.FC_INSTANCE_STATE_STOPPED)
            except Exception as e:
                raise NonRecoverableError("Stop instance {0} failed! The error message is {1}".format(
                    instance_id, e))
        else:
            raise NonRecoverableError(
                'Only when the virtual machine is started can it be stopped.')

    def delete(self):
        instance_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)

        if not instance_id:
            ctx.logger.info('The virtual machine does not exist, skip the delete.')
            return
        if not self.get_vm(instance_id):
            ctx.logger.info('The virtual machine does not exist, skip the delete.')
            return
        try:
            ctx.logger.info('Deleting FusionCompute VM {}.'.format(instance_id))
            self.fc_client.servers.delete(instance_id)
        except Exception as e:
            raise NonRecoverableError("Delete instance {0} failed! The error message is {1}.".format(
                instance_id, e))
        clear_runtime_properties()

    def reboot(self):
        instance_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        instance_state = self.get_instance_state(instance_id)

        if instance_state != fc_constants.FC_INSTANCE_STATE_ACTIVE:
            raise NonRecoverableError('The virtual machine is stopped and cannot be restarted.')

        try:
            ctx.logger.info('Rebooting FusionCompute VM {}.'.format(instance_id))
            self.fc_client.servers.reboot(instance_id)
        except Exception as e:
            raise NonRecoverableError("Reboot instance {0} failed! The error message is {1}.".format(
                instance_id, e))

    def resize(self, **kwargs):
        runtime_properties = ctx.instance.runtime_properties
        instance_id = runtime_properties.get(common_constants.EXTERNAL_ID)
        instance_state = self.get_instance_state(instance_id)
        if instance_state != fc_constants.FC_INSTANCE_STATE_STOPPED:
            ctx.logger.info('current FusionCompute VM status is:{}'.format(instance_state))
            raise NonRecoverableError('The virtual machine is not stopped and cannot modify configure.')

        ctx.logger.info('modify FusionCompute VM configure instance_id:{}, kwargs:{}.'.format(instance_id, kwargs))

        vcpu = kwargs.get('cpus')
        memory = kwargs.get('memory')

        request_data = {}
        if vcpu:
            request_data.update({
                "cpu": {
                    "quantity": vcpu
                }
            })
        if memory:
            request_data.update({
                "memory": {
                    "quantityMB": memory
                }
            })

        try:
            self.fc_client.servers.modify_confige(instance_id, request_data)
            instance_info = self.fc_client.servers.get(instance_id)

            if vcpu:
                instance_info['vmConfig']['cpu'].update({"quantity": vcpu})
            if memory:
                instance_info['vmConfig']['memory'].update({"quantityMB": memory})
            self.update_runtime_properties('compute', instance_info)

            ctx.instance.update()
            ctx.logger.info('modify FusionCompute VM configure DONE :{}.'.format(ctx.instance.runtime_properties))

        except Exception as e:
            raise NonRecoverableError('modify FusionCompute VM configure FAIL :{}'.format(e))

    def modify_display_name(self, **kwargs):
        runtime_properties = ctx.instance.runtime_properties
        instance_id = runtime_properties.get(common_constants.EXTERNAL_ID)
        ctx.logger.info('modify FusionCompute VM name instance_id:{}. kwargs: {}'.format(instance_id, kwargs))

        param_dict = validate_parameter('names', kwargs, not_empty=True)
        old_name, new_name = list(param_dict.items())[0]

        request_data = {
            "name": new_name
        }

        try:
            self.fc_client.servers.modify_confige(instance_id, request_data)
            instance_info = self.fc_client.servers.get(instance_id)
            ctx.logger.info('FusionComputer VM, created instance_info: {}'.format(instance_info))
            instance_info.update({
                "name": new_name,
                "external_name": new_name
            })
            self.update_runtime_properties('compute', instance_info)
            ctx.instance.update()
            ctx.logger.info('modify FusionCompute VM name DONE :{}.'.format(ctx.instance.runtime_properties))
        except Exception as e:
            raise NonRecoverableError('modify FusionCompute VM name FAIL :{}'.format(e))

    def get_vm(self, instance_id):
        return self.fc_client.servers.get(instance_id)
