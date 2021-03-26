# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from abstract_plugin.platforms.common.eip import CommonEip
from cloudify import ctx
from cloudify.utils import convert2bool
from abstract_plugin.platforms.ksyun.restclient import Helper
from abstract_plugin.platforms.common import constants as common_constants
from abstract_plugin.platforms.common.utils import validate_parameter
from abstract_plugin.platforms.ksyun.base import Base
from . import constants as ksyun_constants


class Eip(Base, CommonEip):
    def __init__(self):
        super(Eip, self).__init__()

    def _create_external_eip(self):
        self.update_eip_runtime(self.resource_id)

    @staticmethod
    def update_eip_runtime(eip_id):
        ctx.instance.runtime_properties = {}
        request_body = {
            'AllocationId.1': eip_id
        }
        eip_obj = Helper().execute_request('eip', 'describe_addresses', request_body)['AddressesSet']
        if not eip_obj:
            return eip_obj
        eip_obj = eip_obj[0]
        ctx.instance.runtime_properties[common_constants.EXTERNAL_ID] = eip_obj['AllocationId']
        ctx.instance.runtime_properties[common_constants.EIP_ADDRESS] = eip_obj['PublicIp']
        ctx.instance.runtime_properties[common_constants.EIP_STATUS] = eip_obj['State']
        ctx.instance.runtime_properties[ksyun_constants.KS_EIP_TYPE] = eip_obj.get('InstanceType')
        instance_id = eip_obj.get('InstanceId')
        if instance_id and eip_obj.get('InstanceType') == 'Ipfwd':
            request_body = {
                'InstanceId.1': eip_obj['InstanceId']
            }
            instance_obj = Helper().execute_request('kec', 'describe_instances', request_body)['InstancesSet'][0]
            ctx.instance.runtime_properties[common_constants.EIP_RELATED_INSTANCE_ID] = eip_obj['InstanceId']
            ctx.instance.runtime_properties[common_constants.EIP_RELATED_INSTANCE_NAME] = instance_obj.get(
                'InstanceName')

    def create(self):
        '''
        There will be two situations:
        1.EIP is to be created with no relationship
        2.EIP is to be created with instance and should be associate with instance
        '''
        if not convert2bool(self.resource_config.get('allocate_eip', True)):
            return
        if self.use_external_resource:
            self._create_external_eip()
            return
        resource_config = ctx.node.properties['resource_config']
        ctx.logger.info('Allocate Eip...resource_config:{}'.format(resource_config))
        request_body = {
            'BandWidth': validate_parameter('band_width', resource_config),
            'ChargeType': resource_config.get('charge_type', 'HourlyInstantSettlement'),
        }
        line_id = resource_config.get('line_id', None)
        if line_id:
            request_body['LineId'] = line_id
        ctx.logger.info('Allocate Eip...request_body:{}'.format(request_body))
        eip_obj = Helper().execute_request('eip', 'allocate_address', request_body)
        ctx.logger.info('Allocate Eip successfully....Eip info:{}'.format(eip_obj))
        self.update_eip_runtime(eip_obj.get('AllocationId'))

    def delete(self):
        if not convert2bool(self.resource_config.get('allocate_eip', True)):
            return
        eip_id = ctx.instance.runtime_properties[common_constants.EXTERNAL_ID]
        request_body = {
            'AllocationId': eip_id
        }
        ctx.logger.info('Start release eip with parameters:{}'.format(request_body))
        Helper().execute_request('eip', 'release_address', request_body)
        ctx.logger.info('Finish release eip successfully...')
        ctx.instance.runtime_properties = {}
