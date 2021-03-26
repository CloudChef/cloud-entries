# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from functools import partial

from keystoneauth1.identity import v3
from keystoneauth1.identity import v2
from keystoneauth1 import session
from novaclient import client as nova_client


class OpenStackClient(object):

    def __init__(self):
        self.clients = {
            'nova_client': partial(nova_client.Client, '2')
        }

    @staticmethod
    def get_session(op_config):
        """
        Return keystone session
        :param op_config:
        :return:
        """

        user_domain = op_config.get('OS_USER_DOMAIN_NAME')
        project_domain = op_config.get('OS_PROJECT_DOMAIN_NAME', user_domain)
        user = op_config.get('OS_USERNAME')
        password = op_config.get('OS_PASSWORD')
        project_id = op_config.get('OS_PROJECT_ID')
        auth_url = op_config.get('OS_AUTH_URL')
        verify = op_config.get('insecure', True)

        auth_params = {
            'username': user,
            'password': password,
            'project_id': project_id,
            'auth_url': auth_url
        }

        version_v3 = '/v3' in auth_url

        if version_v3:
            auth_params['user_domain_id'] = user_domain or project_domain
            auth_params['project_domain_id'] = project_domain or user_domain
            auth = v3.Password(**auth_params)
        else:
            auth_params['tenant_id'] = auth_params.pop('project_id')
            auth = v2.Password(**auth_params)
        sess = session.Session(auth=auth, verify=verify)
        return sess

    def create_client(self, client_name, op_config):
        if client_name in self.clients:
            sess = self.get_session(op_config)
            op_client = self.clients[client_name](session=sess)
            return op_client
