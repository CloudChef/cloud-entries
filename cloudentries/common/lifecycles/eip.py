# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from . import constants
from abstract_plugin.platforms.common.base import CommonResource


class CommonEip(CommonResource):

    @staticmethod
    def get_related_vm():
        relationships = ctx.instance.relationships
        for relationship in relationships:
            if relationship.target.node.type in [constants.COMPUTE_NODE_TYPE, constants.WINDOWS_COMPUTE_NODE_TYPE]:
                return relationship.target.instance
        return None
