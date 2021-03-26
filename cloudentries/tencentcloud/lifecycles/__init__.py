# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import ssl
from .network import Network
from .compute import Compute
from .volume import Volume
from .eip import Eip
from .vpc import Vpc
from .oss import Oss
from .securitygroup import SecurityGroup
from abstract_plugin.orchestra_utils import Orchestra_Maps, NETWORK_MAP, COMPUTE_MAP, VOLUME_MAP, SECURITY_GROUP_MAP, \
    VPC_MAP, EIP_MAP, OSS_MAP


ssl._create_default_https_context = ssl._create_unverified_context
cloudentry_id = "yacmp:cloudentry:type:generic-cloud:tencentcloud"
Orchestra_Maps(cloudentry_id, Network, NETWORK_MAP)
Orchestra_Maps(cloudentry_id, Compute, COMPUTE_MAP)
Orchestra_Maps(cloudentry_id, Volume, VOLUME_MAP)
Orchestra_Maps(cloudentry_id, SecurityGroup, SECURITY_GROUP_MAP)
Orchestra_Maps(cloudentry_id, Vpc, VPC_MAP)
Orchestra_Maps(cloudentry_id, Eip, EIP_MAP)
Orchestra_Maps(cloudentry_id, Oss, OSS_MAP)
