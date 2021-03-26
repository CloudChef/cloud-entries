# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common import constants
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter
from abstract_plugin.platforms.ksyun.base import Base
from abstract_plugin.platforms.common.listeners import CommonListener
from abstract_plugin.platforms.ksyun.restclient import Helper


class Listener(Base, CommonListener):
    def __init__(self):
        super(Listener, self).__init__()

    def prepare_params(self, slb_id):
        protocol = validate_parameter('protocol', self.resource_config)
        if self.region == 'cn-hongkong-2' and protocol == 'UDP':
            raise NonRecoverableError('UDP protocol is not supported in Hong Kong!')
        listeners_config = {
            'LoadBalancerId': slb_id,
            'ListenerState': 'start',
            'ListenerName': validate_parameter('name', self.resource_config),
            'ListenerProtocol': protocol,
            'ListenerPort': validate_parameter('port', self.resource_config),
            'Method': validate_parameter('method', self.resource_config),
            'SessionState': 'start' if validate_parameter('session_state', self.resource_config) else 'stop'
        }
        if self.resource_config.get('session_period') and self.resource_config.get('session_state'):
            listeners_config['SessionPersistencePeriod'] = self.resource_config.get('session_period')
        if protocol == 'HTTP':
            cookie_type = validate_parameter('cookie_type', self.resource_config)
            listeners_config['CookieType'] = cookie_type
            if cookie_type == 'RewriteCookie':
                listeners_config['CookieName'] = validate_parameter('cookie_name', self.resource_config)
        ctx.instance.runtime_properties['loadBalancerId'] = self.resource_config.get('loadBalancerId')
        return listeners_config

    def get_health_check_params(self, listener_id):
        health_check_config = {
            'ListenerId': listener_id,
            'HealthCheckState': 'start' if validate_parameter('health_check_state', self.resource_config) else 'stop',
            'HealthyThreshold': self.resource_config.get('healthy_threshold', 5),
            'Interval': self.resource_config.get('interval', 5),
            'Timeout': self.resource_config.get('timeout', 4),
            'UnhealthyThreshold': self.resource_config.get('un_healthy_threshold', 4)
        }
        protocol = self.resource_config.get('protocol')
        if self.resource_config.get('url_path') and protocol == 'HTTP':
            health_check_config['UrlPath'] = self.resource_config.get('url_path')
        if self.resource_config.get('host_name') and protocol == 'HTTP':
            health_check_config['HostName'] = self.resource_config.get('host_name')
        return health_check_config

    @staticmethod
    def update_listener_runtime(listener_id):
        request_body = {
            'ListenerId.1': listener_id
        }
        result = Helper().execute_request('slb', 'describe_listeners', request_body)
        listeners_obj = result.get('ListenerSet')
        if listeners_obj:
            external_slb_id = listeners_obj[0].pop('LoadBalancerId')
            listener_obj = listeners_obj[0]
            ctx.instance.runtime_properties['external_id'] = listener_obj.get('ListenerId')
            ctx.instance.runtime_properties['external_name'] = listener_obj.get('ListenerName')
            ctx.instance.runtime_properties['status'] = listener_obj.get('ListenerState')
            ctx.instance.runtime_properties['external_slb_id'] = external_slb_id
            ctx.instance.runtime_properties.update(listener_obj)
            ctx.instance.update()
        else:
            ctx.logger.info('Listeners does not exist!')

    def create(self):
        slb_id = self.get_related_slb()
        if not slb_id:
            raise NonRecoverableError('Unable to obtain load balancer ID, single node deployment is not supported!')
        listener_params = self.prepare_params(slb_id)
        ctx.logger.info('Attempting to create listeners parameters: {0}'.format(listener_params))
        result = Helper().execute_request('slb', 'create_listeners', listener_params)
        listener_id = result.get('ListenerId')
        if not listener_id:
            raise NonRecoverableError('Listener create failed!')
        self.update_listener_runtime(listener_id)
        ctx.logger.info('Create listeners: {0} successfully'.format(listener_id))
        health_check_params = self.get_health_check_params(listener_id)
        ctx.logger.info('Attempting to create health check parameters: {0}'.format(health_check_params))
        res = Helper().execute_request('slb', 'configure_health_check', health_check_params)
        health_check_id = res.get('HealthCheckId')
        if health_check_id:
            self.update_listener_runtime(listener_id)
            ctx.logger.info(
                'Create listeners: {0} and health check: {1} successfully.'.format(listener_id, health_check_id))
        else:
            raise NonRecoverableError('Create health check failed!')

    def delete(self):
        listener_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        if not listener_id:
            ctx.logger.info('The listener was not created successfully')
            return
        request_body = {
            'ListenerId': listener_id
        }
        result = Helper().execute_request('slb', 'delete_listeners', request_body)
        if result.get('Return'):
            ctx.instance.runtime_properties = {}
            ctx.instance.update()
            ctx.logger.info('Delete listeners: {0} successfully.'.format(listener_id))
        else:
            raise NonRecoverableError('Delete listeners: {0} failed.'.format(listener_id))
