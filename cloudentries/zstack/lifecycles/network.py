# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from .connection import Base
from cloudify.exceptions import NonRecoverableError


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()
        self.client = self.get_client()
        self.endpoint = '/l2-networks'

    def create(self):
        if self.use_external_resource:
            self.write_runtime()
        nsg = self.get_nsg()
        if nsg:
            ctx.instance.runtime_properties['nsg_info'] = nsg.node.properties

    @staticmethod
    def delete():
        ctx.instance.runtime_properties = {}

    def get_network(self, resource_id):
        condition = {
            "resource_id": resource_id
        }
        try:
            resp = self.client.call('get', self.endpoint, body=None, condition=condition).json()
            if resp.get('inventories'):
                return resp['inventories'][0]
        except Exception as e:
            raise NonRecoverableError("Query the zstack 3l-network {0} failed! the error message is {1}".format(
                resource_id, e))

    def get_subnet(self):  # zstack 创建使用subnet, 对应查询3层网络接口
        subnet_id = self.resource_config.get("subnet_id")
        endpoint = "/l3-networks/{}".format(subnet_id)
        try:
            resp = self.client.call('get', endpoint, body=None).json()
            if resp.get('inventories'):
                return resp['inventories'][0]
        except Exception as e:
            raise NonRecoverableError("Query the zstack 3l-network {0} failed! the error message is {1}".format(
                subnet_id, e))

    def write_runtime(self):
        network = self.get_subnet()
        network_runtime = {
            'external_id': network['uuid'],
            'external_name': network['name'],
            'network': network
        }
        ctx.instance.runtime_properties.update(network_runtime)
        ctx.instance.update()
