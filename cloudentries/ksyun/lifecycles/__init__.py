# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from .network import Network
from .compute import Compute
from .volume import Volume
from .security_group import SecurityGroup
from .eip import Eip
from .loadbalancer import LoadBalancer
from .listeners import Listener
from .vpc import Vpc
from abstract_plugin.orchestra_utils import Orchestra_Maps, NETWORK_MAP, COMPUTE_MAP, VOLUME_MAP, SECURITY_GROUP_MAP, \
    VPC_MAP, EIP_MAP, SLB_MAP, LISTENER_MAP

cloudentry_id = "yacmp:cloudentry:type:generic-cloud:ksyun"
Orchestra_Maps(cloudentry_id, Network, NETWORK_MAP)
Orchestra_Maps(cloudentry_id, Compute, COMPUTE_MAP)
Orchestra_Maps(cloudentry_id, Volume, VOLUME_MAP)
Orchestra_Maps(cloudentry_id, SecurityGroup, SECURITY_GROUP_MAP)
Orchestra_Maps(cloudentry_id, Vpc, VPC_MAP)
Orchestra_Maps(cloudentry_id, Eip, EIP_MAP)
Orchestra_Maps(cloudentry_id, LoadBalancer, SLB_MAP)
Orchestra_Maps(cloudentry_id, Listener, LISTENER_MAP)
