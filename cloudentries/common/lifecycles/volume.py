# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from . import constants
from abstract_plugin.platforms.common.base import CommonResource


class CommonVolume(CommonResource):
    @staticmethod
    def get_related_vm():
        relationships = ctx.instance.relationships
        for relationship in relationships:
            if relationship.type == constants.VOLUME_CONTAINED_IN_COMPUTE:
                return relationship.target.instance
        return None
