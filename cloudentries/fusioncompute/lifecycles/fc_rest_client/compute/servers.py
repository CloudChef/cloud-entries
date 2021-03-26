# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from ..common import FusionComputeBase
from cloudify import ctx


class ServersClient(FusionComputeBase):
    IDENTIFIER = 'vms'

    def create(self, urn, server_config):
        uri = self.urn2uri(urn)
        return self.rest_client.post(uri, data=server_config)

    def update(self):
        pass

    def start(self, urn):
        action = '/action/start'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        return self.rest_client.post(uri)

    def stop(self, urn, force=False):
        action = '/action/stop'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        config = {'mode': 'safe' if not force else 'force'}
        return self.rest_client.post(uri, config)

    def clone(self, urn, config):
        action = '/action/clone'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        return self.rest_client.post(uri, data=config)

    def delete(self, urn, is_format=0, hold_time=0, is_reserve_disks=0):
        uri_prefix = self.urn2uri(urn)
        pagination = 'isFormat={}&holdTime={}&isReserveDisks={}'.format(is_format, hold_time, is_reserve_disks)
        uri = '?'.join([uri_prefix, pagination])
        return self.rest_client.delete(uri)

    def attachvol(self, urn, volume_id):
        action = '/action/attachvol'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        config = {'volUrn': volume_id}
        return self.rest_client.post(uri, data=config)

    def detachvol(self, urn, volume_id):
        action = '/action/detachvol'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        config = {'volUrn': volume_id}
        return self.rest_client.post(uri, data=config)

    def modify_confige(self, urn, config):
        server_uri = self.urn2uri(urn)
        ctx.logger.info('server_uri: {}, config: {}'.format(server_uri, config))
        return self.rest_client.put(server_uri, data=config)
