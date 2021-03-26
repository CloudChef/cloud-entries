# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties, set_runtime_properties
from abstract_plugin.platforms.common.network import CommonNetwork
from abstract_plugin.platforms.smartx.restclient import Client, NetworkHelper
from abstract_plugin.platforms.smartx.utils import Base
from abstract_plugin.platforms.common.constants import EXTERNAL_ID
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx


class Network(CommonNetwork, Base):

    def __init__(self):
        super(Network, self).__init__()

    def _prepare_request_body(self):
        dhcp_config = {}

        ip_ranges = self.resource_config.get('ip_ranges')
        if ip_ranges:
            dhcp_config['ip_ranges'] = ip_ranges

        gateway_ip = self.resource_config.get('gateway_ip')
        if gateway_ip:
            dhcp_config['gateway_ip'] = gateway_ip

        cidr = self.resource_config.get('cidr')
        if cidr:
            dhcp_config['cidr'] = cidr

        dhcp_interface_ip = self.resource_config.get('dhcp_interface_ip')
        if dhcp_interface_ip:
            dhcp_config['dhcp_interface_ip'] = dhcp_interface_ip

        dns_servers = self.resource_config.get('dns_servers')
        if dns_servers:
            dhcp_config['dns_servers'] = dns_servers

        network_dict = {
            "vds_id": validate_parameter("vds_id", self.resource_config),
            "name": validate_parameter("name", self.resource_config),
            "vlan_id": validate_parameter('vlan_id', self.resource_config),
            "dhcp_config": dhcp_config
        }

        return network_dict

    def create(self, **kwargs):

        # todo: Create new network

        try:
            with NetworkHelper(Client()) as helper:
                network_id = validate_parameter('resource_id', self.resource_config)
                subnet_id = validate_parameter('subnet_id', self.resource_config)
                ctx.logger.info('Use existed SmartX network: {}, subnet: {}.'.format(network_id, subnet_id))

                network_info = helper.get_vds(network_id)
                subnet_info = helper.get_network(network_id, subnet_id)

                network_index = ctx.node.name[-1] if ctx.node.name[-1].isdigit() else 0
                set_runtime_properties('network_index', network_index, ctx.instance)

                set_runtime_properties('subnet_info', subnet_info, ctx.instance)
                extra_values = {
                    EXTERNAL_ID: subnet_id,
                }
                self.save_runtime_properties('network', network_info, extra_values)
        except Exception as e:
            raise NonRecoverableError('Create network from SmartX failed: {}.'.format(e))

    def delete(self, **kwargs):

        # todo: Delete network created by cloudify

        # if not self.use_external_resource:
        #     try:
        #         network_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        #         subnet_id = ctx.instance.runtime_properties.get('subnet_info', {}).get('Id')
        #         ctx.logger.info('Deleting SmartX network {}.'.format(network_id))
        #         with NetworkHelper(Client(**self.connection_config)) as helper:
        #             job_info = helper.delete_network(vds_id, network_id)
        #             self.wait_job(helper, job_info['job_id'])
        #
        #         ctx.logger.info('SmartX network {} deleted.'.format(network_id))
        #     except Exception as e:
        #         raise NonRecoverableError(
        #             'Delete SmartX network {} failed: {}'.format(network_id, e.message))
        clear_runtime_properties()
