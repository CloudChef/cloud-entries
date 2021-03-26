from abstract_plugin.platforms.common.eip import CommonEip
from cloudify import ctx
from abstract_plugin.platforms.tencentcloud.restclient import NetworkHelper
from abstract_plugin.platforms.common import constants


class Eip(CommonEip):
    def __init__(self):
        super(Eip, self).__init__()

    def create(self):
        '''
        There will be two situations:
        1.EIP is to be created with no relationship
        2.EIP is to be created with instance and should be associate with instance
        '''
        resource_config = ctx.node.properties['resource_config']
        request_body = {
            'InternetMaxBandwidthOut': resource_config.get('InternetMaxBandwidthOut', None)
        }
        ctx.logger.info('Allocate Eip...resource_config:{}'.format(resource_config))
        ctx.logger.info('Allocate Eip...request_body:{}'.format(request_body))
        eip_obj = NetworkHelper().allocate_eip(**request_body)
        ctx.instance.runtime_properties[constants.EXTERNAL_ID] = eip_obj['AddressId']
        ctx.instance.runtime_properties[constants.EIP_ADDRESS] = eip_obj['AddressIp']
        ctx.instance.runtime_properties[constants.EIP_STATUS] = eip_obj['AddressStatus']

        ctx.logger.info('Allocate Eip successfully....Eip info:{}'.format(eip_obj))

    def delete(self):
        eip_id = ctx.instance.runtime_properties[constants.EXTERNAL_ID]
        ctx.logger.info('Start release eip...')
        NetworkHelper().release_eip(eip_id)
        ctx.logger.info('Finish release eip successfully...')
