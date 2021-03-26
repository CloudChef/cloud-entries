# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import ipaddress

from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from abstract_plugin.platforms.ksyun.restclient import Helper
from abstract_plugin.platforms.common.utils import validate_parameter
from .base import Base
from cloudify.exceptions import NonRecoverableError


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()

    def create(self):
        if self.use_external_resource:
            self.resource_id = ctx.node.properties['resource_config']['subnet_id']
            self.write_runtime(self.resource_id)
        else:
            self._create()
        nsg = self.get_nsg()
        if nsg:
            ctx.instance.runtime_properties['nsg_info'] = nsg.node.properties

    def _create(self):
        ctx.logger.info('Start to create subnet...')
        cidr = validate_parameter('cidr_block', self.resource_config)
        ip_range_from, ip_range_to = self.get_ip_range(cidr)
        params = {
            'AvailabilityZone': validate_parameter('available_zone_id', self.resource_config),
            'SubnetName': self.resource_config.get('subnet_name'),
            'CidrBlock': validate_parameter('cidr_block', self.resource_config),
            'SubnetType': validate_parameter('subnet_type', self.resource_config),
            'DhcpIpFrom': ip_range_from,
            'DhcpIpTo': ip_range_to,
            'GatewayIp': validate_parameter('gateway', self.resource_config),
            'VpcId': validate_parameter('resource_id', self.resource_config),
            'Dns1': validate_parameter('dns1', self.resource_config),
            'Dns2': self.resource_config.get('dns2'),
        }
        params = dict((k, v) for k, v in list(params.items()) if v)
        ctx.logger.info('Try to create subnet with parameters {}'.format(params))
        res = Helper().execute_request('vpc', 'create_subnet', params)
        subnet_id = res['Subnet']['SubnetId']
        self.write_runtime(subnet_id)
        ctx.logger.info("Create subnet {0} successfully".format(subnet_id))

    @staticmethod
    def get_ip_range(cidr):
        net = ipaddress.ip_network(cidr)
        return str(net[0]), str(net[-1])

    def delete(self):
        subnet_id = ctx.instance.runtime_properties.get('external_id')
        if subnet_id:
            ctx.logger.info("Start to delete subnet {0}...".format(subnet_id))
            Helper().execute_request('vpc', 'delete_subnet', {'SubnetId': subnet_id})
            ctx.logger.info(" Delete subnet {0} successfully".format(subnet_id))
        else:
            ctx.logger.info("Can not find subnet in runtime properties, skip the step.")

    def get_network(self, resource_id):
        query_params = {'SubnetId.1': resource_id}
        network = Helper().execute_request('vpc', 'describe_subnets', query_params).get('SubnetSet')
        if not network:
            raise NonRecoverableError("Subnet {0} not exists".format(resource_id))
        else:
            return network[0]

    def write_runtime(self, subnet_id):
        network = self.get_network(subnet_id)
        network_runtime = {
            'external_id': network.get('SubnetId'),
            'external_name': network.get('SubnetName'),
            'cidr_block': network.get('CidrBlock'),
            'dns1': network.get('Dns1'),
            'dns2': network.get('Dns2'),
            'dhcp_to': network.get('DhcpIpTo'),
            'dhcp_from': network.get('DhcpIpFrom'),
            'network': network
        }
        ctx.instance.runtime_properties.update(network_runtime)
        ctx.instance.update()
        ctx.logger.info("Subnet: {0}".format(network_runtime))
