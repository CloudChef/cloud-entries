# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from .base import Base


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()
        self.conn = self.get_client()

    def create(self):
        ctx.logger.info('Creating FusionAccess Network {}.'.format(self.node_properties))
        if self._use_external_resource():  # support use external network only
            return True
        return

    def _use_external_resource(self):
        if not self.use_external_resource:
            return False
        resource_id = self.resource_config.get('resource_id')   # portgroup_id
        self.update_runtime_properties(resource_id)
        return True

    def describe_network(self, resource_id):
        url = "/describePortGroups"
        params = {
            "siteId": self.region,
            "clusterId": self.zone
        }
        network_info = self.conn.common_request("post", url, params)
        for portgroup in network_info.get("portGroups"):
            if portgroup.get("portGroupId") == int(resource_id):
                return portgroup
        return {}

    def update_runtime_properties(self, resource_id):
        network_info = self.describe_network(resource_id)
        network = {
            "id": resource_id,
            "name": network_info.get("portGroupName"),
            "vlan": network_info.get("vlanId"),
            "switch_id": network_info.get("dvSwitchId"),
            "description": network_info.get("description"),
            "ip_address": "",
            "cidr": "",
            "gateway": "",
            "dns_servers": "",
            "router": "",
            "ip_pool": self.resource_config.get("ip_allocation_method")
        }
        network_runtime = {
            'external_id': resource_id,
            'external_name': network.get("name"),
            "use_external_resource": self.use_external_resource,
            "ip_allocation_method": self.resource_config.get("ip_allocation_method"),
            "network": network
        }
        ctx.instance.runtime_properties.update(network_runtime)
        ctx.instance.update()

    def delete(self):
        ctx.instance.runtime_properties = {}
        ctx.instance.update()
        return
