# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common import constants as common_constants
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter
from abstract_plugin.platforms.ksyun.base import Base
from abstract_plugin.platforms.common.slb import CommonSlb
from abstract_plugin.platforms.ksyun.restclient import Helper
from . import constants as ksyun_constants


class LoadBalancer(Base, CommonSlb):
    def __init__(self):
        super(LoadBalancer, self).__init__()

    def prepare_params(self):
        params = {
            'VpcId': validate_parameter('vpc', self.resource_config),
            'LoadBalancerName': validate_parameter('name', self.resource_config),
            'Type': validate_parameter('load_balancer_type', self.resource_config)
        }
        slb_type = params.get('Type')
        if slb_type != ksyun_constants.KS_SLB_PUBLIC_TYPE:
            params.update({'SubnetId': validate_parameter('subnet', self.resource_config)})
        return params

    def get_listeners_from_load_balancer(self, slb_id):
        desc_params = {
            'Filter.1.Name': 'load-balancer-id',
            'Filter.1.Value.1': slb_id
        }
        listener_objs = Helper().execute_request('slb', 'describe_listeners', desc_params)['ListenerSet']
        listener_ids = []
        for listener_obj in listener_objs:
            listener_ids.append(listener_obj.get('ListenerId'))
        return listener_ids

    def del_listeners(self, listener_ids):
        for listener_id in listener_ids:
            del_listener_params = {
                'ListenerId': listener_id
            }
            del_listeners = Helper().execute_request('slb', 'delete_load_balancer', del_listener_params)
            if del_listeners.get('Return'):
                ctx.logger.info('Finish delete listeners: {0} successfully...'.format(listener_id))
            else:
                ctx.logger.info('Finish delete listeners: {0} failed...'.format(listener_id))

    def modify_state(self, slb_id, status):
        params = {
            'LoadBalancerId': slb_id,
            'LoadBalancerState': status
        }
        res = Helper().execute_request('slb', 'describe_load_balancers', {'LoadBalancerId.1': slb_id})
        if not res.get('LoadBalancerDescriptions'):
            ctx.logger.info('The loadbalancer "{0}" was deleted or not created.'.format(slb_id))
            return
        res = Helper().execute_request('slb', 'modify_load_balancer', params)
        return res.get('LoadBalancerState')

    @staticmethod
    def update_slb_runtime(slb_id):
        request_body = {
            'LoadBalancerId.1': slb_id
        }
        result = Helper().execute_request('slb', 'describe_load_balancers', request_body)
        slb_objs = result.get('LoadBalancerDescriptions')
        if slb_objs:
            slb_obj = slb_objs[0]
            vpc_id = slb_obj.get('VpcId')
            vpcs = Helper().execute_request('vpc', 'describe_vpcs', {'VpcId.1': vpc_id})['VpcSet']
            ctx.instance.runtime_properties.update({
                'external_id': slb_obj.get('LoadBalancerId'),
                'external_name': slb_obj.get('LoadBalancerName'),
                'status': slb_obj.get('LoadBalancerState'),
                'IsWaf': slb_obj.get('IsWaf'),
                'networkType': 'internet' if slb_obj.get('Type') == 'public' else slb_obj.get('Type'),
                'VpcId': slb_obj.get('VpcId'),
                'network': vpcs[0].get('VpcName') if vpcs else '',
                'vipAddress': slb_obj.get('PublicIp'),
                'ListenersCount': slb_obj.get('ListenersCount'),
                'AssociateState': slb_obj.get('State'),
                'IpVersion': slb_obj.get('IpVersion'),
                'ChargeType': slb_obj.get('ChargeType')
            })
            ctx.instance.update()
        else:
            ctx.logger.info('LoadBalancer does not exist!')
            ctx.instance.runtime_properties['status'] = 'lost'
            ctx.instance.update()

    def associate_eip(self, instance_id):
        eip_id = validate_parameter('eip', self.resource_config)
        ctx.logger.info('Start associate EIP:{} to Instance:{}'.format(eip_id, instance_id))
        associate_params = {
            'AllocationId': eip_id,
            'InstanceType': 'Slb',
            'InstanceId': instance_id
        }
        res = Helper().execute_request('eip', 'associate_address', associate_params)
        if res.get('Return'):
            ctx.logger.info('Finish associate EIP successfully...')
        else:
            ctx.logger.info('Finish associate EIP failed...')

    def create(self):
        create_params = self.prepare_params()
        ctx.logger.info('Attempting to create loadbalancer parameters: {0}.'.format(create_params))
        result = Helper().execute_request('slb', 'create_load_balancer', create_params)
        ctx.logger.info('Create loadbalancer successfully....slb info: {0}.'.format(result))
        slb_id = result.get('LoadBalancerId')
        if not slb_id:
            raise NonRecoverableError('LoadBalancer create failed!')
        self.update_slb_runtime(slb_id)
        if create_params.get('Type') == ksyun_constants.KS_SLB_PUBLIC_TYPE:
            self.associate_eip(slb_id)
            self.update_slb_runtime(slb_id)

    def start(self):
        slb_id = ctx.instance.runtime_properties.get('external_id')
        if not slb_id:
            ctx.logger.info('Start failed, loadbalancer is not exist.')
            return
        res = self.modify_state(slb_id, 'start')
        if res == 'start':
            self.update_slb_runtime(slb_id)
            ctx.logger.info('Stop loadbalancer: {0} successfully.'.format(slb_id))
        else:
            ctx.logger.info('Stop loadbalancer: {0} failed.'.format(slb_id))

    def stop(self):
        slb_id = ctx.instance.runtime_properties.get('external_id')
        if not slb_id:
            ctx.logger.info('Start failed, loadbalancer is not exist.')
            return
        res = self.modify_state(slb_id, 'stop')
        if res == 'stop':
            self.update_slb_runtime(slb_id)
            ctx.logger.info('Stop loadbalancer: {0} successfully.'.format(slb_id))
        else:
            ctx.logger.info('Stop loadbalancer: {0} failed.'.format(slb_id))

    def delete(self):
        slb_id = ctx.instance.runtime_properties.get(common_constants.EXTERNAL_ID)
        if not slb_id:
            ctx.logger.info('The loadbalancer was not created successfully')
            return
        request_body = {
            'LoadBalancerId.1': slb_id
        }
        res = Helper().execute_request('slb', 'describe_load_balancers', request_body)
        if not res.get('LoadBalancerDescriptions'):
            ctx.logger.info('The loadbalancer: {0} was not created or deleted'.format(slb_id))
            return
        slb_obj = res.get('LoadBalancerDescriptions')[0]
        if slb_obj.get('ListenersCount') != 0:
            listener_ids = self.get_listeners_from_load_balancer(slb_id)
            self.del_listeners(listener_ids)
        ctx.logger.info('Attempting to delete loadbalancer: {0}.)'.format(slb_id))
        del_params = {
            'LoadBalancerId': slb_id
        }
        del_result = Helper().execute_request('slb', 'delete_load_balancer', del_params)
        if del_result.get('Return'):
            ctx.logger.info('Finish delete loadbalancer: {0} successfully...'.format(slb_id))
        else:
            ctx.logger.info('Finish delete loadbalancer: {0} failed...'.format(slb_id))
