# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from . import constants
from abstract_plugin.platforms.common.base import CommonResource


class CommonListener(CommonResource):

    @staticmethod
    def get_related_slb():
        target_instance_runtime_props = {}
        relationships = ctx.instance.relationships
        for relationship in relationships:
            if relationship.type == constants.SLB_CONNECTED_TO_LISTENER:
                target_instance_runtime_props = relationship.target.instance.runtime_properties
                break
        slb_id = target_instance_runtime_props.get('external_id')
        return slb_id
