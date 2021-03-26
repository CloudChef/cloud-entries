# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.connector import Connector
from abstract_plugin.platforms.common.constants import (
    EXTERNAL_ID,
    EXTERNAL_NAME,
    EXTERNAL_HOSTNAME
)


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()

    @staticmethod
    def set_base_runtime_props(resource_id=None, name=None, hostname=None):
        rt_props = ctx.instance.runtime_properties
        rt_props[EXTERNAL_ID] = resource_id
        rt_props[EXTERNAL_NAME] = name
        if hostname:
            rt_props[EXTERNAL_HOSTNAME] = hostname
