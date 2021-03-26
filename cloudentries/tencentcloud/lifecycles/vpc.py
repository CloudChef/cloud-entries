from abstract_plugin.platforms.common.vpc import CommonVpc
from abstract_plugin.platforms.tencentcloud.utils import Base
from abstract_plugin.platforms.common.utils import validate_parameter
from .restclient import NetworkHelper
from cloudify import ctx


class Vpc(CommonVpc, Base):
    def create(self):
        ctx.logger.info('Start to create Vpc...')
        vpc_name = validate_parameter('vpc_name', self.resource_config)
        cidr_block = validate_parameter('cidr_block', self.resource_config)
        request_body = {
            'VpcName': vpc_name,
            'CidrBlock': cidr_block
        }
        ctx.logger.info('Try to create Vpc with parameters {}'.format(request_body))
        vpc_info = NetworkHelper().create_vpc(request_body)
        ctx.instance.runtime_properties['vpc_info'] = vpc_info
        ctx.logger.info('Created Vpc Successfully...')

    def delete(self):
        ctx.logger.info('Start to delete Vpc...')
        vpc_info = ctx.instance.runtime_properties['vpc_info']
        vpc_id = vpc_info.get('VpcId')
        ctx.logger.info('Try to delete Vpc:{}'.format(vpc_id))
        request_body = {
            'VpcId': vpc_id
        }
        NetworkHelper().delete_vpc(request_body)
        ctx.logger.info('Delete Vpc:{} successfully...'.format(vpc_id))
