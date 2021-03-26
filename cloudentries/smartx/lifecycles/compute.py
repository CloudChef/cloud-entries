# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
import time

from abstract_plugin.platforms.common.compute import CommonCompute
from abstract_plugin.platforms.smartx.restclient import Client, ComputeHelper
from abstract_plugin.platforms.smartx.utils import Base
from abstract_plugin.platforms.common.constants import EXTERNAL_ID, EXTERNAL_NAME, EXTERNAL_HOSTNAME
from abstract_plugin.platforms.common.utils import (
    validate_parameter,
    cidr_to_netmask,
    clear_runtime_properties
)
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from cloudify.utils import decrypt_password
import abstract_plugin.platforms.common.constants as common_constants
from .constants import SMARTX_INSTANCE_STATE_STOPPED


optional_keys = ['cpu', 'firmware', 'node_ip', 'cpu_model']


class Compute(Base, CommonCompute):

    def __init__(self):
        super(Compute, self).__init__()
        self.action_mapper = {
            "modify_display_name": self.modify_display_name,
            "resize": self.resize
        }

    def _get_network_info(self, network):
        rp_props = network.instance.runtime_properties
        return rp_props.get('network_info'), rp_props.get('subnet_info')

    def _get_nic_info(self, network, network_info, nameservers):
        resource_config = network.node.properties['resource_config']

        ip_allocation_method = resource_config.get('ip_allocation_method')
        ip_type = "ipv4"
        ip_address = ""
        netmask = ""
        gateway = ""

        if ip_allocation_method == common_constants.IP_POOL:
            node_id = network.node.id
            ip_pool_info = self.get_ip_pool_info(node_id)
            if ip_pool_info:
                gateway = ip_pool_info.get('gateway')
                nameservers = ip_pool_info.get('dns_servers')
                netmask = cidr_to_netmask(ip_pool_info.get('cidr'))[1]
                ip_address = ip_pool_info.get('ip')

        elif ip_allocation_method == common_constants.DHCP:
            ip_type = "ipv4_dhcp"
        elif ip_allocation_method == common_constants.STATIC_IP:
            gateway = network_info.get('gateway')
            nameservers = network_info.get('dns_servers')
            netmask = cidr_to_netmask(network_info.get('cidr'))[1]
            ip_address = network_info.get('ip')
        result = {
            "cloud_init_nic": {
                'ip_address': ip_address,
                'netmask': netmask,
                'type': ip_type
            },
            "gateway": gateway,
            "nameservers": nameservers
        }
        return result

    def _get_nic_params(self, network, nameservers):
        network_info, subnet_info = self._get_network_info(network)
        subnet_id = subnet_info['uuid']
        ovsbr_name = network_info.get('ovsbr_name')
        vlan_info = {'vlan_id': subnet_info.get('vlan_id')}

        nic = {'vlans': [vlan_info], 'vlan_uuid': subnet_id, 'ovs': ovsbr_name}
        all_network_info = self.get_network_info(network)
        if all_network_info:
            ip_address = all_network_info.get('ip')
            if ip_address:  # not dhcp
                nic['ip_address'] = ip_address
        nic_info = self._get_nic_info(network, all_network_info, nameservers)
        nic_info['nic'] = nic
        return nic_info

    def _get_nics_params(self):
        nics, cloud_init_nics, gateway, nameservers = [], [], None, []
        networks, primary_network = self.get_networks(), self.get_primary_network()  # noqa
        nic_index = 0
        for network in networks:
            nic_info = self._get_nic_params(network, nameservers)
            nics.append(nic_info.get('nic'))
            cloud_init_nic = nic_info.get('cloud_init_nic')
            cloud_init_nic['nic_index'] = nic_index
            nic_index += 1
            cloud_init_nics.append(nic_info.get('cloud_init_nic'))
            gateway, nameservers = nic_info.get('gateway'), nic_info.get('nameservers') or []
            # nameserver max items is 3, min items is 1
            nameservers = nameservers[:3]

        return nics, cloud_init_nics, gateway, nameservers

    def _get_cloud_init_data(self, hostname, password, nics, nameservers, gateway=""):

        cloud_init_data = {
            "default_user_password": password,
            "hostname": hostname,
            "network_info": {
                "nameservers": nameservers or ['114.114.114.114'],
                "networks": nics,
                "public_keys": [],
                "user_data": ""
            }
        }
        if gateway:
            cloud_init_data["network_info"].update({
                "gateway": gateway
            })
        return cloud_init_data

    def _get_instances_params(self):

        vm_name = self.resource_config.get('instance_name')
        hostname = None
        if not vm_name:
            vm_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or vm_name
        password = decrypt_password(self.resource_config.get('password'))
        description = self.resource_config.get('description', '')
        ha = self.resource_config.get('ha', False)
        vcpu = validate_parameter('CPU', self.resource_config, not_empty=True)
        memory = int(validate_parameter('Memory', self.resource_config, not_empty=True)) << 20
        image_id = validate_parameter('image_id', self.resource_config, not_empty=True)
        nested_virtualization = self.resource_config.get('nested_virtualization', False)
        # nics
        nics, cloud_init_nics, gateway, nameservers = self._get_nics_params()
        cloud_init_data = self._get_cloud_init_data(
            hostname, password, cloud_init_nics, nameservers, gateway)

        data = {
            "vm_name": vm_name,
            "status": "stopped",
            "description": description,
            'image_id': image_id,
            'is_full_copy': False,
            "ha": ha,
            "vcpu": vcpu,
            "cpu": {"topology": {"cores": vcpu, "sockets": 1}},
            "memory": memory,
            "nested_virtualization": nested_virtualization,
            "nics": nics,
            "cloud_init": cloud_init_data
        }
        self.set_optional_values(self.resource_config, data, optional_keys)

        return data

    def clone_instance(self, helper):
        create_type = self.resource_config.get('create_type', '')
        if (not create_type) or (create_type == "create"):
            return False
        clone_params, hostname, src_vm_id = self.prepare_clone_params(helper)

        ctx.logger.info("Cloning SmartX params:{}".format(clone_params))
        job_info = helper.clone_vm(src_vm_id, clone_params)

        vm_id = self.wait_job(helper, job_info['job_id'])
        vm_info = helper.get_vm(vm_id)
        ctx.logger.info('Clone SmartX vm successfully.')

        extra_values = {EXTERNAL_HOSTNAME: hostname}
        self.save_runtime_properties('compute', vm_info, extra_values)
        return True

    def create(self, **kwargs):
        with ComputeHelper(Client()) as helper:
            if self._create_external_instance(helper):
                return
            if self.clone_instance(helper):
                return
            data = self._get_instances_params()
            ctx.logger.info(
                'Creating SmartX VM with parameters: {}'.format(
                    json.dumps(self.hiden_password(data), indent=2)))
            job_info = helper.create_vm_from_template(data)

            vm_id = self.wait_job(helper, job_info['job_id'])
            vm_info = helper.get_vm(vm_id)
            ctx.logger.info('Create VM from SmartX successfully.')

            extra_values = {EXTERNAL_HOSTNAME: data['cloud_init']['hostname']}
            self.save_runtime_properties('compute', vm_info, extra_values)

    def _create_external_instance(self, helper):
        if not self.use_external_resource:
            return False
        instance_id = validate_parameter('resource_id', self.node_properties)
        ctx.logger.info('Use existed SmartX VM: {}.'.format(instance_id))
        vm_info = helper.get_vm(instance_id)
        extra_values = {EXTERNAL_HOSTNAME: validate_parameter('vm_name', vm_info)}
        self.save_runtime_properties('compute', vm_info, extra_values)
        self.update_networks()
        return True

    def save_primary_ip(self, vm):
        primary_network = self.get_primary_network()
        if primary_network:
            subnet_id = primary_network.node.properties.get('resource_config').get('subnet_id')
            nics = vm.get('nics', [])
            for nic in nics:
                if nic['vlan_uuid'] == subnet_id:
                    ctx.instance.runtime_properties['ip'] = nic['ip_address']
                    break

    def update_networks(self):
        ips = []
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        with ComputeHelper(Client()) as helper:
            vm = helper.get_vm(vm_id)
            nics = vm.get('nics', [])
        if self.use_external_resource:
            # There is not network connected to instance,instance is external.
            net_info = {'ip': nics[0].get('ip_address') or '', 'name': 'PrivateIpAddress'}
            ctx.instance.runtime_properties['networks'] = {"Network": net_info}
            ctx.instance.runtime_properties['ip'] = nics[0].get('ip_address')
        else:
            # Create by CMP.
            networks = self.get_networks()
            runtime_networks = ctx.instance.runtime_properties.get('networks')
            for network in networks:
                subnet_info = network.instance.runtime_properties['subnet_info']
                for nic in nics:
                    if network.node.properties.get('resource_config').get('subnet_id') == nic['vlan_uuid']:
                        subnet_info['ip'] = nic['ip_address'] or ''
                network_node_id = network.node.id
                runtime_networks[network_node_id].update(subnet_info)
                ctx.instance.runtime_properties.update({'networks': runtime_networks})
        for nic in nics:
            ips.append(nic.get("ip_address"))
        ctx.instance.runtime_properties['ips'] = ips
        ctx.instance.update()

    def wait_vm_ready(self, helper, job_id, vm_id, timeout=600, interval=15):

        self.wait_job(helper, job_id)
        rest_time = timeout

        while rest_time > 0:
            vm = helper.get_vm(vm_id)
            nics = vm['nics']
            flag = 0
            for nic in nics:
                if not nic.get('ip_address'):
                    flag = 1
                    ctx.logger.debug("Wait for SmartX vm's nics ready, sleep {} seconds.".format(interval))
                    time.sleep(interval)
                    rest_time -= interval
            if not flag:
                return
        raise NonRecoverableError('Get SmartX VM ips failed after {} seconds, '
                                  'ensure vmtools and cloud-init already installed on template.'.format(timeout))

    def start(self, **kwargs):
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Staring SmartX VM {}.'.format(vm_id))

        with ComputeHelper(Client()) as helper:
            job_info = helper.start_vm(vm_id)
            self.wait_vm_ready(helper, job_info['job_id'], vm_id)
            vm = helper.get_vm(vm_id)
            if not self.use_external_resource:  # Create by CMP.
                self.save_primary_ip(vm)
        ctx.logger.info('SmartX VM {} started.'.format(vm_id))
        self.update_networks()

    def reboot(self, **kwargs):
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Rebooting SmartX VM {}.'.format(vm_id))
        with ComputeHelper(Client()) as helper:
            job_info = helper.reboot_vm(vm_id)
            self.wait_job(helper, job_info['job_id'])
        ctx.logger.info('SmartX VM {} rebooted.'.format(vm_id))

    def stop(self, **kwargs):
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not vm_id:
            ctx.logger.warn('Id of vm not found, skip stopping.')
            return

        ctx.logger.info('Stopping SmartX VM {}.'.format(vm_id))
        with ComputeHelper(Client()) as helper:
            if not self.get_vm(helper, vm_id):
                ctx.logger.info('SmartX VM:{} is not exist, no need to stop'.format(vm_id))
                return
            job_info = helper.stop_vm(vm_id)
            self.wait_job(helper, job_info['job_id'])
        ctx.logger.info('SmartX VM {} stopped.'.format(vm_id))

    def delete(self, **kwargs):
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not vm_id:
            ctx.logger.warn('Id of vm not found, skip stopping.')
            return

        ctx.logger.info('Deleting SmartX VM {}.'.format(vm_id))
        with ComputeHelper(Client()) as helper:
            if not self.get_vm(helper, vm_id):
                ctx.logger.info('SmartX VM:{} is not exist, no need to delete'.format(vm_id))
                return
            data = {'include_volumes': True}
            job_info = helper.delete_vm(vm_id, json.dumps(data))
            self.wait_job(helper, job_info['job_id'])
        clear_runtime_properties()
        ctx.logger.info('SmartX VM {} deleted.'.format(vm_id))

    def modify_display_name(self, **kwargs):
        new_name = validate_parameter(ctx.instance.id, kwargs.get('names', {}))
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Updating name of SmartX VM {}.'.format(vm_id))

        with ComputeHelper(Client()) as helper:
            helper.modify_display_name(vm_id, new_name)
        ctx.instance.runtime_properties[EXTERNAL_NAME] = new_name
        ctx.logger.info('Updated name of SmartX VM {}.'.format(vm_id))

    def hiden_password(self, data):
        # hide password
        log_data = dict(data)
        if log_data.get('cloud_init') and log_data['cloud_init'].get('default_user_password'):
            log_data['cloud_init']['default_user_password'] = '********'
        return log_data

    def get_networks(self):
        networks = super(Compute, self).get_networks()
        return sorted(networks, key=lambda network: network.instance.runtime_properties['network_index'])

    def get_status(self, helper, instance_id):
        vm_info = helper.get_vm(instance_id)
        return vm_info.get("status")

    def resize(self, **kwargs):
        vm_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        with ComputeHelper(Client()) as helper:
            vm_state = self.get_status(helper, vm_id)
            if vm_state != SMARTX_INSTANCE_STATE_STOPPED:
                ctx.logger.error("The virtual machine's status should be stopped, current status is:{}".
                                 format(vm_state))
                return
            new_cpu = validate_parameter('cpus', kwargs)
            new_memory = validate_parameter('memory', kwargs)

            if (not new_cpu) and (not new_memory):
                ctx.logger.error(
                    "The param `CPU` and `Memory` is required, received param is:{}".format(kwargs))
                return
            vm_info = helper.get_vm(vm_id)
            _cpu = vm_info['cpu']
            _params = {
                'ha': vm_info['ha']
            }
            if new_cpu:
                _cpu['topology']['cores'] = new_cpu
                _params.update({'vcpu': new_cpu})
            _params.update({'cpu': _cpu})
            if new_memory:
                new_memory = new_memory << 20  # memory->Byte
                _params.update({'memory': new_memory})
            job_info = helper.modify_configure(vm_id, _params)
            ret = self.wait_job(helper, job_info['job_id'])
            ctx.logger.info("smartx resized result: {}".format(ret))
            vm_info = helper.get_vm(vm_id)
        self.save_runtime_properties('compute', vm_info)
        ctx.logger.info("smartx resized done")

    def prepare_clone_params(self, helper):
        vm_name = self.resource_config.get('instance_name')
        src_vm_id = self.resource_config.get("template_id")
        node_ip = self.resource_config.get("node_ip", "")
        description = self.resource_config.get("description", "")

        hostname = None
        if not vm_name:
            vm_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or vm_name

        nics, _, _, _ = self._get_nics_params()
        src_vm_info = helper.get_vm(src_vm_id)

        clone_params = {
            "vm_name": vm_name,
            "status": "stopped",
            "description": description,
            "vcpu": src_vm_info.get("vcpu"),
            "memory": src_vm_info.get("memory"),
            "ha": src_vm_info.get("ha"),
            "disks": [],
            "node_ip": src_vm_info.get("node_ip"),
            "nics": nics,
            "auto_schedule": False if node_ip else True
        }
        return clone_params, hostname, src_vm_id

    def get_vm(self, helper, instance_id):
        return helper.get_vm(instance_id)
