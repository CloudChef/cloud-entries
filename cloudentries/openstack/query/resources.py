# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from .client import OpenStackClient
from novaclient import exceptions as nova_exceptions


class OpenStackResource(object):

    def __init__(self, config):
        self.client = OpenStackClient().create_client('nova_client', config)

    def get_instances(self, params):
        res = []

        for server_id in params:
            try:
                resp = self.client.servers.get(server_id)
                while True:
                    if resp.ready():
                        obj = resp.value
                        break
                if obj:
                    server = {'id': str(obj.id),
                              'name': str(obj.name),
                              'status': str(obj.status),
                              'volumes_attached': str(
                        getattr(obj, 'os-extended-volumes:volumes_attached'))
                    }
                    if hasattr(obj, 'health_status'):
                        server['health_status'] = str(obj['health_value']['health_status'])
                    res.append(server)
            except nova_exceptions.NotFound as e:
                pass

        return res
