# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from ..common import FusionComputeBase
from cloudify import ctx


class VolumesClient(FusionComputeBase):
    IDENTIFIER = 'volumes'

    def list(self, urn, limit=100, offset=0):
        uri_prefix = '/'.join([self.urn2uri(urn), self.IDENTIFIER])
        pagination = "limit={limit}&offset={offset}".format(limit=limit, offset=offset)
        uri = "?".join([uri_prefix, pagination])
        return self.rest_client.get(uri)

    def create(self, urn, config):
        uri = "/".join([self.urn2uri(urn), self.IDENTIFIER])
        return self.rest_client.post(uri, data=config)

    def delete(self, urn, is_format=0):
        uri_perfix = self.urn2uri(urn)
        pagination = "isFormat={}".format(is_format)
        uri = "?".join([uri_perfix, pagination])
        return self.rest_client.delete(uri)

    def expandvol(self, urn, config):
        action = '/action/expandvol'
        server_uri = self.urn2uri(urn)
        uri = server_uri + action
        ctx.logger.info('uri: {}, data: {}'.format(uri, config))
        return self.rest_client.post(uri, data=config)
