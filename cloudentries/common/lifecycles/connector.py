# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify.utils import convert2bool
from .utils import get_instance_or_source_node_properties, get_connection_config


class Connector(object):
    def __init__(self):
        self.node_properties = get_instance_or_source_node_properties()
        self.connection_config = get_connection_config()
        self.resource_config = self.node_properties['resource_config']
        self.connection_config['region'] = self.resource_config.get("region")
        self.region = self.resource_config.get('region')
        self.zone = self.resource_config.get('available_zone_id')
        self.use_external_resource = convert2bool(self.resource_config.get('use_external_resource', False)) or \
            convert2bool(self.node_properties.get('use_external_resource', False))
        self.resource_id = self.resource_config.get('resource_id') or self.node_properties.get('resource_id')
