# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from abstract_plugin.platforms.common.security_group import CommonSecurityGroup
from abstract_plugin.platforms.tencentcloud.restclient import NetworkHelper
from abstract_plugin.platforms.tencentcloud.utils import Base
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from abstract_plugin.platforms.common import constants


class SecurityGroup(CommonSecurityGroup, Base):

    def __init__(self):
        super(SecurityGroup, self).__init__()

    def create(self, **kwargs):
        if self.use_external_resource:
            securitygroup_id = validate_parameter('resource_id', self.resource_config)
            try:
                sg_info = NetworkHelper().list_securitygroups(ids=[securitygroup_id])[0]
                ctx.logger.debug("Use existed tencentcloud security group: {}.".format(securitygroup_id))
                self.set_base_runtime_props(resource_id=sg_info.get('SecurityGroupId'),
                                            name=sg_info.get('SecurityGroupName'))
                ctx.instance.runtime_properties['nsg_info'] = sg_info
            except Exception as e:
                raise NonRecoverableError("Create security group failed: {}.".format(e))
        else:
            securitygroup_name = validate_parameter('securitygroup_name', self.resource_config)
            securitygroup_description = self.resource_config.get('securitygroup_description', '-')
            securitygroup_policyset = self.resource_config.get('rules')
            request_body = {
                'GroupName': securitygroup_name,
                'GroupDescription': securitygroup_description,
                'SecurityGroupPolicySet': securitygroup_policyset
            }
            try:
                sg_info = NetworkHelper().create_securitygroup_with_policies(request_body)
                self.set_base_runtime_props(resource_id=sg_info.get('SecurityGroupId'),
                                            name=sg_info.get('SecurityGroupName'))
                ctx.instance.runtime_properties['nsg_info'] = sg_info
            except Exception as e:
                raise NonRecoverableError("Create security group failed: {}.".format(e))

    def start(self, **kwargs):
        pass

    def reboot(self, **kwargs):
        pass

    def stop(self, **kwargs):
        pass

    def delete(self, **kwargs):
        if self.use_external_resource:
            clear_runtime_properties()
        else:
            sg_id = ctx.instance.runtime_properties[constants.EXTERNAL_ID]
            request_body = {
                'SecurityGroupId': sg_id
            }
            try:
                NetworkHelper().delete_securitygroup(request_body)
            except Exception as e:
                ctx.logger.info('Delete security group failed...messages:{}'.format(e))
            clear_runtime_properties()
