# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

# common
NODE_INSTANCE = 'node-instance'
RELATIONSHIP_INSTANCE = 'relationship-instance'
COMPUTE_CONNECTED_TO_NETWORK = 'cloudchef.abstract.relationships.compute_connected_to_network'
VOLUME_CONTAINED_IN_COMPUTE = 'cloudchef.abstract.relationships.volume_contained_in_compute'
NETWORK_CONNECTED_TO_SECURITY_GROUP = 'cloudchef.abstract.relationships.network_connected_to_security_group'
COMPUTE_CONNECTED_TO_SECURITY_GROUP = 'cloudchef.abstract.relationships.compute_connected_to_security_group'
SLB_CONNECTED_TO_LISTENER = 'cloudchef.relationships.sdx.nodes.contained_in.resource.iaas.network.load_balancer.generic_slb'    # NOQA
COMPUTE_CONNECTED_TO_EIP = \
    'cloudchef.relationships.sdx.nodes.connected_to.resource.iaas.network.floating_ip.generic_eip'

COMPUTE_NODE_TYPE = 'cloudchef.nodes.Compute'
WINDOWS_COMPUTE_NODE_TYPE = 'cloudchef.nodes.WindowsCompute'
EXTERNAL_ID = 'external_id'
EXTERNAL_NAME = 'external_name'
EXTERNAL_HOSTNAME = 'external_hostname'

EIP_ADDRESS = 'eip_address'
EIP_STATUS = 'eip_status'
EIP_RELATED_INSTANCE_ID = 'instance_id'
EIP_RELATED_INSTANCE_NAME = 'instance_name'


InstanceStatusMapper = {
    "configured": ["configured"],
    "configuring": ["configuring"],
    "creating": ["scheduling", "provisioning", "creating"],
    "deleted": ["deleted"],
    "deleting": ["recycling", "shutting-down", "terminating"],
    "install fail": ["install fail"],
    "lost": ["unknown", "undefined", "terminated"],
    "purged": ["purged"],
    "started": ["active", "running", "start"],
    "starting": ["rebuilding", "starting", "rebooting", "launching", "restarting", "staging", "initializing"],
    "stopped": ["stopped", "suspended", "terminated", "repairing", "stop", "unavailable"],
    "stopping": ["stopping", "stop", "pause", "hibernating", "suspending"],
    "uninitialized": ["uninitialized"]
}


PowerStatusMapper = {
    "POWERED_OFF": ["stopped", "shutdown", "terminating"],
    "POWERED_ON": ["running", "rebuilding", "launching", "restarting", "rebooting", "shuttingdown", "pending"],
    "SUSPENDED": ["suspended"],
    "UNKNOWN": ["unknown", "undefined", "terminated"]
}

# IP allocation methods
DHCP = 'DHCP'
IP_POOL = 'IP_POOL'
STATIC_IP = 'STATIC_IP'
