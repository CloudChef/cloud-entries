# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.vpc import CommonVpc
from abstract_plugin.platforms.ksyun.restclient import Helper
from abstract_plugin.platforms.common.utils import validate_parameter
from .base import Base


class Vpc(Base, CommonVpc):
    def __init__(self):
        super(Vpc, self).__init__()

    def create(self):
        if self.use_external_resource:
            self.write_runtime(self.resource_id)
        else:
            self._create()

    def _create(self):
        ctx.logger.info('Start to create VPC...')
        params = {
            "VpcName": self.resource_config.get('vpc_name'),
            "CidrBlock": validate_parameter('cidr_block', self.resource_config),
        }
        ctx.logger.info('Try to create Vpc with parameters {}'.format(params))
        res = Helper().execute_request('vpc', 'create_vpc', params)
        vpc_id = res['Vpc']['VpcId']
        self.write_runtime(vpc_id)
        ctx.logger.info('Create Vpc {0} successfully'.format(vpc_id))

    def delete(self):
        vpc_id = ctx.instance.runtime_properties.get('external_id')
        if vpc_id:
            ctx.logger.info("Start to delete VPC {0}...".format(vpc_id))
            Helper().execute_request('vpc', 'delete_vpc', {'VpcId': vpc_id})
            ctx.logger.info(" Delete VPC {0} successfully".format(vpc_id))
        else:
            ctx.logger.info("Can not find vpc in runtime properties, skip the step.")

    def write_runtime(self, vpc_id):
        vpc = self.get_vpc(vpc_id)
        ctx.instance.runtime_properties.update({
            "external_id": vpc['VpcId'],
            "external_name": vpc['VpcName'],
            "cidr_block": vpc['CidrBlock'],
            "vpc_info": vpc
        })

    @staticmethod
    def get_vpc(vpc_id):
        params = {"VpcId.1": vpc_id}
        res = Helper().execute_request('vpc', 'describe_vpcs', params)
        vpcs = res['VpcSet']
        if vpcs:
            return vpcs[0]
        else:
            raise NonRecoverableError("Can not find VPC {0} in the account.".format(vpc_id))
