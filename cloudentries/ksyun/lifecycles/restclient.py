# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password, hide_password
from abstract_plugin.platforms.common.utils import validate_parameter, get_connection_config
from kscore.session import get_session


class Helper(object):
    def __init__(self):
        self.connection_config = get_connection_config()
        self.resource_config = ctx.node.properties['resource_config']
        self.region = validate_parameter('region', self.resource_config)
        self.ks_access_key_id = validate_parameter('access_key_id', self.connection_config)
        self.ks_secret_access_key = decrypt_password(validate_parameter('access_key_secret', self.connection_config))
        self.domain = self.connection_config.get('domain')

    def get_client(self, service):
        session = get_session()
        if self.domain:
            session.set_domain(self.domain)
        client = session.create_client(service_name=service,
                                       region_name=self.region,
                                       ks_access_key_id=self.ks_access_key_id,
                                       ks_secret_access_key=self.ks_secret_access_key,
                                       use_ssl=False)
        return client

    def execute_request(self, service, request_method, request_body):
        try:
            client = self.get_client(service)
            return getattr(client, request_method)(**request_body)
        except Exception as e:
            raise NonRecoverableError(
                'Service name:{},execute request:{} failed,parameters:{},error messages:{}'.format(service,
                                                                                                   request_method,
                                                                                                   hide_password(
                                                                                                       request_body),
                                                                                                   e))
