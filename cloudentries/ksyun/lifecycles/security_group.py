# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from .base import Base
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.security_group import CommonSecurityGroup
from abstract_plugin.platforms.ksyun.restclient import Helper


class SecurityGroup(Base, CommonSecurityGroup):
    def __init__(self):
        super(SecurityGroup, self).__init__()

    def create(self):
        if self.use_external_resource:
            self.write_runtime(self.resource_id)

    def delete(self):
        if self.use_external_resource:
            ctx.instance.runtime_properties = {}

    def get_security_group(self, resource_id):
        query_params = {'SecurityGroupId.1': resource_id}
        sg = Helper().execute_request('vpc', 'describe_security_groups', query_params).get('SecurityGroupSet')
        if not sg:
            raise NonRecoverableError("Security Group {0} not exists".format(resource_id))
        else:
            return sg[0]

    def write_runtime(self, resource_id):
        sg = self.get_security_group(resource_id)
        sg_runtime = {
            'external_id': sg['SecurityGroupId'],
            'external_name': sg['SecurityGroupName'],
            'security_group': sg,
            'nsg_info': self.resource_config
        }
        ctx.instance.runtime_properties.update(sg_runtime)
        ctx.instance.update()
