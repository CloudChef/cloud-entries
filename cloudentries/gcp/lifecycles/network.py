# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
from cloudify import ctx
from abstract_plugin.platforms.common.network import CommonNetwork
from abstract_plugin.platforms.gcp.base import Base
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import clear_runtime_properties, set_runtime_properties


class Network(Base, CommonNetwork):
    def __init__(self):
        super(Network, self).__init__()

    def create(self):
        # Create a network instance
        compute = self.get_client()

        resource_bundle_config = self.resource_config['resource_bundle_config']
        network_id = resource_bundle_config.get('network_id', 'default')

        try:
            network_info = compute.networks().get(
                project=self.project,
                network=network_id).execute()

            subnet_id = resource_bundle_config.get('subnet_id') or self.get_default_subnet_id(network_info)

            self.check_subnet(network_info, subnet_id)
            self.save_network_info(network_info, subnet_id)
            self.save_subnet_info(compute, subnet_id)

        except Exception as e:
            raise NonRecoverableError('Get network info from Google Cloud Platform failed: {}'.format(e))

    def get_default_subnet_id(self, network_info):
        subnetworks = network_info.get('subnetworks') or []
        for subnetwork in subnetworks:
            if self.region in subnetwork:
                subnet_id = subnetwork.split('/')[-1]
                return subnet_id

    def check_subnet(self, network_info, subnet_id):
        subnetworks = network_info.get('subnetworks') or []
        for subnetwork in subnetworks:
            if subnet_id in subnetwork and self.region in subnetwork:
                return

        raise NonRecoverableError(
            'Vpc network {} has no subnet {} in region {}'.format(
                json.dumps(network_info, indent=2), subnet_id, self.region))

    def save_subnet_info(self, compute, subnet_id):
        subnet_info = compute.subnetworks().get(
            project=self.project,
            region=self.region,
            subnetwork=subnet_id).execute()

        set_runtime_properties('subnet_info', subnet_info, ctx.instance)

    def save_network_info(self, network_info, subnet_id):
        network_info['subnet_id'] = subnet_id
        self.save_runtime_properties('network', network_info)

    def delete(self):
        # Delete the network instance
        clear_runtime_properties()
