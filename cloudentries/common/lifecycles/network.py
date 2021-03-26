# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from . import constants
from abstract_plugin.platforms.common.base import CommonResource


class CommonNetwork(CommonResource):
    @staticmethod
    def get_nsg():
        for relationship in ctx.instance.relationships:
            if relationship.type == constants.NETWORK_CONNECTED_TO_SECURITY_GROUP:
                return relationship.target
        return None
