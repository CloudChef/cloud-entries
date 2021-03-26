# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from .base import Base
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.security_group import CommonSecurityGroup


class SecurityGroup(Base, CommonSecurityGroup):
    def __init__(self):
        super(SecurityGroup, self).__init__()
        self.connect = self.get_client()

    def create(self):
        if self.use_external_resource:
            self.update_runtime_properties(self.resource_id)

    def delete(self):
        if self.use_external_resource:
            ctx.instance.runtime_properties = {}

    def get_security_group(self, resource_id):
        query_params = {'Action': 'DescribeFirewall', 'Region': self.connection_config['region'], 'FWId': resource_id}
        sg = self.connect.get('/', query_params)
        if not sg:
            raise NonRecoverableError("Security Group {0} not exists".format(resource_id))
        else:
            return sg['DataSet'][0]

    def update_runtime_properties(self, resource_id):
        sg = self.get_security_group(resource_id)
        sg_runtime = {
            'external_id': sg['FWId'],
            'external_name': sg['Name'],
            'security_group': sg,
            'nsg_info': self.node_properties
        }
        ctx.instance.runtime_properties.update(sg_runtime)
        ctx.instance.update()
