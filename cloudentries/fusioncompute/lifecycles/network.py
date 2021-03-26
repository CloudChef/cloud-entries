# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from abstract_plugin.platforms.fusioncompute.base import Base
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import clear_runtime_properties, set_runtime_properties


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()
        self.fc_client = self.get_client()

    def create(self):
        dvs_id = self.resource_config['resource_id']
        port_group_id = self.resource_config['subnet_id']

        try:
            dvs_info = self.fc_client.dvswitchs.get(dvs_id)
            port_group_info = self.fc_client.portgroups.get(port_group_id)
        except Exception as e:
            raise NonRecoverableError('Get network info from FusionCompute failed: {}'.format(e))

        self.update_runtime_properties('network', dvs_info)
        set_runtime_properties('subnet_info', port_group_info, ctx.instance)

    def delete(self):
        clear_runtime_properties()
