# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify_agent.rpc_client.rpc_client import RpcClient
from cloudify_agent.rpc_client.operations import retrieve_or_release_ip_from_rabbitmq
from cloudify.utils import cidr_to_netmask, format_route_rules
from . import constants
from .utils import get_instance_or_source_node_properties
from abstract_plugin.platforms.common.base import CommonResource


class CommonCompute(CommonResource):

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def reboot(self):
        raise NotImplementedError

    @staticmethod
    def get_networks():
        networks = [rel.target for rel in ctx.instance.relationships
                    if rel.type == constants.COMPUTE_CONNECTED_TO_NETWORK]
        if not networks:
            raise NonRecoverableError("VM is not connected to any network and subnet")
        return networks

    def get_primary_network(self):
        networks = self.get_networks()
        for network in networks:
            resource_config = network.node.properties['resource_config']
            if resource_config.get('management'):
                return network
        return networks[0]

    def get_primary_network_info(self):
        primary_network = self.get_primary_network()
        if primary_network.node.properties.get('resource_config').get('use_external_resource'):
            return primary_network.node.properties['resource_config']
        else:
            return primary_network.instance.runtime_properties['subnet_info']

    def get_subnet(self):
        '''
        Whether get subnet from resource_config or from subnet_info depend on use_external_resource
        resource_config:{"subnet_id":'12345678'}
        subnet_info:{"SubnetId":'12345678'}
        '''
        primary_network_info = self.get_primary_network_info()
        return primary_network_info.get('subnet_id') or primary_network_info.get('SubnetId')

    def get_subnets(self):
        networks = self.get_networks()
        return [network.node.properties['resource_config']['subnet_id'] for network in networks]

    @staticmethod
    def _get_nsg_related_to_compute():
        for relationship in ctx.instance.relationships:
            if relationship.type == constants.COMPUTE_CONNECTED_TO_SECURITY_GROUP:
                return relationship.target.instance.runtime_properties
        return None

    def _get_nsg_related_to_network(self):
        networks = self.get_networks()
        for network in networks:
            network_runtime = network.instance.runtime_properties
            if network_runtime.get('nsg_info'):
                return network_runtime
        return None

    def get_nsg(self):
        nsg = self._get_nsg_related_to_compute() or self._get_nsg_related_to_network()
        if not nsg:
            raise NonRecoverableError("Compute or network should connect to security group in blueprint!")
        return nsg['nsg_info']

    def get_nsg_id(self):
        return self.get_nsg()['resource_id']

    def get_eip(self):
        for rel in ctx.instance.relationships:
            if rel.type == constants.COMPUTE_CONNECTED_TO_EIP:
                return rel.target.instance
        return None

    def get_eip_node(self):
        for rel in ctx.instance.relationships:
            if rel.type == constants.COMPUTE_CONNECTED_TO_EIP:
                return rel.target.node
        return None

    @staticmethod
    def get_instance_names(retry_num=5, retry_interval=15):
        if ctx.workflow_id == 'heal':
            display_name = ctx.instance.runtime_properties.get(constants.EXTERNAL_NAME)
            hostname = ctx.instance.runtime_properties.get(constants.EXTERNAL_HOSTNAME)
            if display_name and hostname:
                return display_name, hostname

        action = 'provision'
        if ctx.workflow_id == 'scale':
            action = 'scale'

        network_info = CommonCompute().get_network_info()
        if not network_info:
            ip = None
        else:
            ip = network_info.get('ip')

        try:
            body = dict(deployment_id=ctx.deployment.id,
                        node_id=ctx.node.id,
                        node_instance_id=ctx.instance.id,
                        action=action,
                        ip=ip)

            client = RpcClient(action='get_vm_names')
            client_close = False
            retry_time = 0
            while retry_time < retry_num:
                ctx.logger.debug(
                    "Attempt to get vm names from rabbitmq "
                    "with body:{0}, retry {1} times.".format(
                        body, retry_time))
                result = client.call(body)
                if result.get('return_code') == 'True':
                    client.close()
                    client_close = True
                    display_name = result.get('display_name')
                    hostname = result.get('name')
                    if not display_name:
                        display_name = ctx.instance.id
                    return display_name, hostname
                else:
                    retry_time += 1
                    time.sleep(retry_interval)
            else:
                ctx.logger.warn("Get vm names from rabbitmq failed after 5 times, "
                                "attempt to generate randomly.")
                client.close()
                client_close = True
                display_name = ctx.instance.id
                hostname = None
                return display_name, hostname

        except Exception as e:
            if not client_close:
                client.close()
            ctx.logger.warn("Get vm names from rabbitmq failed: {}, "
                            "attempt to generate randomly.".format(e))
            display_name = ctx.instance.id
            return display_name, hostname

    def _get_private_ip_in_compute_node(self):
        self.node_properties = get_instance_or_source_node_properties()
        return self.node_properties['resource_config'].get('private_ip_address')

    def get_network_info(self, network=None):
        if not network:
            network = self.get_primary_network()
        network_node_id = network.node.id
        compute_node_id = ctx.node.id
        resource_config = network.node.properties['resource_config']
        ctx.logger.info('resource_config:{}'.format(resource_config))
        ctx.logger.info('network_node_id:{}'.format(network_node_id))
        ctx.logger.info('ctx_node_id:{}'.format(compute_node_id))
        ip_allocation_method = resource_config.get('ip_allocation_method')

        network_info = {}

        if ip_allocation_method == constants.IP_POOL:
            if ctx.workflow_id == 'heal':
                network_info = ctx.instance.runtime_properties['ip_pool_info'][network_node_id]
            else:
                network_info = self.retrieve_netinfo_from_rabbitmq(network_node_id)
        elif ip_allocation_method == constants.STATIC_IP:
            network_info.update({
                'ip': resource_config['ip_address'].get(compute_node_id),
                'cidr': resource_config.get('cidr'),
                'gateway': resource_config.get('gateway'),
                'netmask': cidr_to_netmask(resource_config.get('cidr'))[1]
            })
        else:
            ip_allocation_method = constants.DHCP
        runtime_networks = ctx.instance.runtime_properties.get('networks', {})
        runtime_networks.update({
            network_node_id: {
                'ip': network_info.get('ip'),
                'gateway': network_info.get('gateway'),
                'cidr': network_info.get('cidr'),
                'netmask': network_info.get('netmask'),
                'network_profile_id': resource_config.get('network_profile_id'),
                'ip_allocation_method': ip_allocation_method,
                'subnet_id': self.get_subnet(),
                'management': resource_config.get('management') or False
            }
        })
        ctx.instance.runtime_properties.update({'networks': runtime_networks})
        ctx.logger.info('current runtimes:{}'.format(ctx.instance.runtime_properties))
        ctx.instance.update()
        return network_info

    def get_ip(self, network=None):
        network_info = self.get_network_info(network)
        if not network_info:
            return
        ctx.logger.info('VM network: {}'.format(network_info))
        return network_info.get('ip')

    @staticmethod
    def release_ip_from_ip_pool():
        if ctx.type == 'relationship-instance':
            node_id = ctx.source.node.id
            instance_id = ctx.source.instance.id
        else:
            node_id = ctx.node.id
            instance_id = ctx.instance.id
        body = dict(deployment_id=ctx.deployment.id,
                    server_node_id=node_id,
                    server_instance_id=instance_id,
                    ip_action='release')
        ctx.logger.debug("Attempt to release ip from rabbitmq.")
        retrieve_or_release_ip_from_rabbitmq(action='release_ip', body=body)

    def release_ip_in_delete_operation(self):
        if ctx.instance.runtime_properties.get('ip_pool_info'):
            if not ctx.workflow_id == 'heal':
                self.release_ip_from_ip_pool()
                ctx.instance.runtime_properties = {}
            else:
                ctx.instance.runtime_properties = dict(
                    ip_pool_info=ctx.instance.runtime_properties.get('ip_pool_info'),
                    routes=ctx.instance.runtime_properties.get('routes'),
                    dns_servers=ctx.instance.runtime_properties.get('dns_servers'))

    def retrieve_netinfo_from_rabbitmq(self, network_node_id):
        if ctx.type == 'relationship-instance':
            node_id = ctx.source.node.id
            ctx_instance = ctx.source.instance
            instance_id = ctx_instance.id
        else:
            node_id = ctx.node.id
            ctx_instance = ctx.instance
            instance_id = ctx_instance.id

        body = dict(deployment_id=ctx.deployment.id,
                    server_node_id=node_id,
                    server_instance_id=instance_id,
                    ip_action='retrieve')

        body['port_node_id'] = '_'.join([node_id, network_node_id])
        body['port_instance_id'] = '_'.join([node_id, network_node_id])

        retrieve_ip_flag = '_'.join(['retrieve_ip', instance_id, network_node_id])
        result = ctx_instance.runtime_properties.get(retrieve_ip_flag)
        ctx.logger.info("retrieve_ip_flag result:{} .".format(result))
        if not result:
            ctx.logger.debug("Attempt to retrieve ip from rabbitmq")
            result = retrieve_or_release_ip_from_rabbitmq(
                action='retrieve_ip', body=body)
            ctx.logger.debug(
                "Retrieve ip {} from RabbitMQ successfully.".format(result))
            ctx_instance.runtime_properties[retrieve_ip_flag] = result
        network_info = self.save_retrieved_info(network_node_id, result, ctx.instance)
        return network_info

    def save_retrieved_info(self, network_node_id, retrieve_info, ctx_instance):
        network = dict()
        network['ip'] = retrieve_info.get('ip_address')
        network['cidr'] = retrieve_info.get('cidr')
        network['netmask'] = cidr_to_netmask(network['cidr'])[1] if retrieve_info.get('cidr') else None
        network['gateway'] = retrieve_info.get('gateway')
        network['dns_servers'] = retrieve_info.get('dns_servers') or list()
        network['routes'] = retrieve_info.get('routes') or list()
        format_route_rules(network)

        ip_pool_info = ctx_instance.runtime_properties.get('ip_pool_info') or dict()
        ip_pool_info[network_node_id] = network
        ctx_instance.runtime_properties['ip_pool_info'] = ip_pool_info

        self._extension_runtime_properties(ctx_instance, 'routes', network['routes'])
        self._extension_runtime_properties(ctx_instance, 'dns_servers', network['dns_servers'])
        return network

    @staticmethod
    def _extension_runtime_properties(ctx_instance, target_property, add_values):
        values = ctx_instance.runtime_properties.get(target_property) or list()
        values.extend(add_values)
        ctx_instance.runtime_properties[target_property] = values
        ctx_instance.update()

    @staticmethod
    def get_ip_pool_info(network_node_id):
        return ctx.instance.runtime_properties.get('ip_pool_info', {}).get(network_node_id, {})
