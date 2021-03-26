# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.fusioncompute.client import FusionCompute
from abstract_plugin.platforms.common.connector import Connector
from abstract_plugin.platforms.common import constants


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()

    def get_client(self):
        connection = FusionCompute(self.connection_config)
        client = connection.connection()
        return client

    @staticmethod
    def update_runtime_properties(resource_type, info=None, extra_values={}):
        if info:
            info_key = '_'.join([resource_type, 'info'])
            required_values = {
                constants.EXTERNAL_ID: info.get('urn'),
                constants.EXTERNAL_NAME: info.get('name'),
                info_key: info
            }
            ctx.instance.runtime_properties.update(required_values)

        ctx.instance.runtime_properties.update(extra_values)
        ctx.instance.update()
