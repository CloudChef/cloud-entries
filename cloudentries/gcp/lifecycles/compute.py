# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json

from abstract_plugin.platforms.gcp.base import Base
from abstract_plugin.platforms.common.compute import CommonCompute
from abstract_plugin.platforms.common import constants as common_constants
from abstract_plugin.platforms.common.utils import (
    validate_parameter,
    clear_runtime_properties
)
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from . import constants as gcp_constants


class Compute(Base, CommonCompute):

    def __init__(self):
        super(Compute, self).__init__()

    def _get_network_params(self, network):
        network_info, subnet_info = self._get_network_and_subnet_info(network)
        node_id = network.node.id

        interfaces_config = {
            'network': network_info['selfLink'],
            'subnetwork': subnet_info['selfLink'],
            'accessConfigs': [
                {
                    'type': 'ONE_TO_ONE_NAT',
                    'name': node_id,
                }
            ],
        }

        ip_address = self.get_ip(network)
        if ip_address:
            interfaces_config['networkIP'] = ip_address

        return interfaces_config

    def _get_network_interfaces(self):
        network_params = []
        networks = self.get_networks()
        for network in networks:
            network_info = self._get_network_params(network)
            network_params.append(network_info)
        return network_params

    @staticmethod
    def _get_network_and_subnet_info(network):
        rp_props = network.instance.runtime_properties
        return rp_props.get('network_info'), rp_props.get('subnet_info')

    @staticmethod
    def _get_image_project_and_name(image_id):
        image_project, image_name = image_id.split('/')
        return image_project, image_name

    @staticmethod
    def _get_size_and_link_from_image(compute, image_project, image_family):
        image_response = compute.images().getFromFamily(project=image_project, family=image_family).execute()
        disk_size = image_response.get('diskSizeGb', '')
        self_link = image_response.get('selfLink', '')
        return disk_size, self_link

    def _prepare_request_params(self, compute):
        flavor = self.resource_config['flavor']
        machine_response = compute.machineTypes().get(
            project=self.project,
            zone=self.zone,
            machineType=flavor).execute()
        machine_type = machine_response.get('selfLink')
        default_vm_name, default_hostname = self.get_instance_names()
        vm_name = self.resource_config.get('instance_name', default_vm_name) or ctx.instance.id
        vm_name = vm_name.replace('_', '-').lower()
        image_id = validate_parameter('image_id', self.resource_config, not_empty=True)
        image_project, image_family = self._get_image_project_and_name(image_id)
        disk_size, image_self_link = self._get_size_and_link_from_image(compute, image_project, image_family)

        hostname = self.resource_config.get('hostname') or '.'.join([vm_name, self.zone, self.project])
        disk_name = vm_name.lower() + '-os-disk'
        description = self.resource_config.get('description', '')
        network_config = self._get_network_interfaces()

        config = {
            'name': vm_name,
            'hostname': hostname,
            'description': description,
            # Instance specifications
            'machineType': machine_type,

            "displayDevice": {
                "enableDisplay": False,
            },

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    "mode": "READ_WRITE",
                    'initializeParams': {
                        'diskName': disk_name,
                        'sourceImage': image_self_link,
                        'diskSizeGb': disk_size
                    }
                }
            ],
            "canIpForward": False,
            'networkInterfaces': network_config,

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                "scopes": [
                    "https://www.googleapis.com/auth/devstorage.read_write",
                    "https://www.googleapis.com/auth/logging.write"
                ],
            }],

            'metadata': {
                'items': [],
            }
        }

        return config

    def _create_external_instance(self, compute):
        if not self.use_external_resource:
            return False

        ctx.logger.info('Create an existed Google Cloud Platform VM: {}'.format(self.resource_id))

        instance_info = compute.instances().get(
            project=self.project,
            zone=self.zone,
            instance=self.resource_id).execute()
        self.save_runtime_properties('compute', instance_info)
        self.update_runtime_properties(self.resource_id)

        return True

    def create(self):
        # Creates an instance resource in the specified project using the data included in the request.
        compute = self.get_client()
        if self._create_external_instance(compute):
            return

        ctx.logger.info('Create instance by params: {}'.format(
            json.dumps(self.resource_config, indent=2)))

        config = self._prepare_request_params(compute)

        ctx.logger.info(
            'Creating instance by config: {}'.format(
                json.dumps(config, indent=2)))

        operation = compute.instances().insert(
            project=self.project,
            zone=self.zone,
            body=config).execute()

        self._wait_for_operation(compute, self.project, self.zone, operation['name'])
        instance_id = config['name']
        instance_info = self.get_vm_info(compute, instance_id)

        extra_values = {
            common_constants.EXTERNAL_HOSTNAME: config['hostname'],
            'ip': instance_info['networkInterfaces'][0]['networkIP'],
        }
        self.save_runtime_properties('compute', instance_info, extra_values)
        self.update_runtime_properties(instance_id)
        ctx.logger.info(
            'The instance was created successfully. result:{}'.format(
                json.dumps(instance_info, indent=2)))

    def update_network(self, compute, instance_id):
        ips = []
        networks = {}
        vm_info = self.describe_instance(compute, instance_id)
        network_interfaces = vm_info['networkInterfaces']
        for index, network in enumerate(network_interfaces):
            network['ip'] = network['networkIP']
            network['name'] = network['subnetwork'].split("/")[-1]
            networks['Network' + str(index)] = network
            ips.append(network.get("ip"))
        ctx.instance.runtime_properties['ips'] = ips
        return networks

    def save_nat_ip(self, vm_info):
        ctx.instance.runtime_properties['nat_ip_info'] = vm_info['networkInterfaces'][0].get('accessConfigs')
        if ctx.instance.runtime_properties['nat_ip_info']:
            ctx.instance.runtime_properties['ip_address'] = ctx.instance.runtime_properties['nat_ip_info'][0]['natIP']

    def start(self):
        vm_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        ctx.logger.info('Starting VM of Google Cloud Platform')

        compute = self.get_client()
        vm_status = self.get_vm_status(compute, vm_id)

        if vm_status == gcp_constants.GCP_INSTANCE_STATE_RUNNING:
            ctx.logger.info('The virtual machine is already on. It does not need to be started.')
            return
        elif vm_status == gcp_constants.GCP_INSTANCE_STATE_STOPPED:
            try:
                ctx.logger.info('Starting VM {} of Google Cloud Platform.'.format(vm_id))
                operation = compute.instances().start(
                    project=self.project,
                    zone=self.zone,
                    instance=vm_id).execute()

                self._wait_for_operation(compute, self.project, self.zone, operation['name'])

                vm_info = self.describe_instance(compute, vm_id)
                self.save_nat_ip(vm_info)

            except Exception as e:
                raise NonRecoverableError("Start instance {0} failed! The error message is {1}".format(
                    vm_id, e))
        else:
            raise NonRecoverableError(
                'Only when the virtual machine is stopped can it be started.')
        self.update_runtime_properties(vm_id)
        ctx.logger.info("Start instance {0} successfully".format(vm_id))

    def stop(self):
        vm_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        if not vm_id:
            ctx.logger.info('The virtual machine does not exist, skip the stop.')
            return
        compute = self.get_client()
        if not self.get_vm(compute, vm_id):
            ctx.logger.info('The virtual machine does not exist, skip the stop.')
            return
        vm_status = self.get_vm_status(compute, vm_id)

        if vm_status == gcp_constants.GCP_INSTANCE_STATE_STOPPED:
            ctx.logger.info('The virtual machine has been turned off. It does not need to be shut down.')
            return
        elif vm_status == gcp_constants.GCP_INSTANCE_STATE_RUNNING:
            try:
                ctx.logger.info('Stopping VM {} of Google Cloud Platform.'.format(vm_id))
                operation = compute.instances().stop(
                    project=self.project,
                    zone=self.zone,
                    instance=vm_id).execute()

                self._wait_for_operation(compute, self.project, self.zone, operation['name'])

            except Exception as e:
                raise NonRecoverableError("Stop instance {0} failed! The error message is {1}".format(
                    vm_id, e))
        else:
            raise NonRecoverableError(
                'Only when the virtual machine is started can it be stopped.')
        self.update_runtime_properties(vm_id)
        ctx.logger.info("Stop instance {0} successfully".format(vm_id))

    def reboot(self):
        vm_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        ctx.logger.info('Reboot the instance {}.'.format(vm_id))
        self.stop()
        self.start()
        self.update_runtime_properties(vm_id)
        ctx.logger.info("Reboot instance {0} successfully".format(vm_id))

    def get_vm_status(self, compute, vm_id):
        res = self.describe_instance(compute, vm_id)
        if res:
            return res['status']
        else:
            raise NonRecoverableError('The virtual machine does not exist.')

    def delete(self):
        # Deletes the specified Instance resource.
        vm_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        if not vm_id:
            ctx.logger.info('The virtual machine does not exist, skip the delete.')
            return

        compute = self.get_client()
        if not self.get_vm(compute, vm_id):
            ctx.logger.info('The virtual machine does not exist, skip the delete.')
            return
        try:
            ctx.logger.info('Deleting VM {} of Google Cloud Platform.'.format(vm_id))
            operation = compute.instances().delete(
                project=self.project,
                zone=self.zone,
                instance=vm_id).execute()

            self._wait_for_operation(compute, self.project, self.zone, operation['name'])

        except Exception as e:
            raise NonRecoverableError("Delete instance {0} failed! The error message is {1}.".format(
                vm_id, e))
        clear_runtime_properties()
        ctx.logger.info("Delete instance {0} successfully".format(vm_id))

    def update_runtime_properties(self, instance_id):
        compute = self.get_client()
        vm_info = self.get_vm_info(compute, instance_id)
        ctx.instance.runtime_properties['vm_info'] = vm_info
        networks = self.update_network(compute, instance_id)
        ctx.instance.runtime_properties.update({
            "vm_info": vm_info,
            "networks": networks
        })
        ctx.instance.update()

    def get_vm(self, compute, vm_id):
        return self.describe_instance(compute, vm_id)
