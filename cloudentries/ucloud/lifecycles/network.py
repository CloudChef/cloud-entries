# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from .base import Base
from cloudify.exceptions import NonRecoverableError


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()
        self.connect = self.get_client()

    def create(self):
        if self.use_external_resource:
            self.update_runtime_properties(self.resource_id)
        nsg = self.get_nsg()
        if nsg:
            ctx.instance.runtime_properties['nsg_info'] = nsg.node.properties.get('resource_config', {})

    def delete(self):
        ctx.instance.runtime_properties = {}

    def get_network(self, resource_id):
        query_params = {
            'Region': self.connection_config['region'],
            'VPCIds.0': resource_id,
            'Action': 'DescribeVPC'}
        network = self.connect.get('/', query_params)
        if not network.get('DataSet'):
            raise NonRecoverableError("VPC {0} not exists".format(resource_id))
        else:
            return network['DataSet'][0]

    def update_runtime_properties(self, resource_id):
        network = self.get_network(resource_id)
        network_runtime = {
            'external_id': network['VPCId'],
            'external_name': network['Name'],
            'network': network
        }
        ctx.instance.runtime_properties.update(network_runtime)
        ctx.instance.update()
