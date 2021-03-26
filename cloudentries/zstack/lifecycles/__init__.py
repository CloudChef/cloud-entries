# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from .network import Network
from .compute import Compute
from .volume import Volume
from abstract_plugin.orchestra_utils import Orchestra_Maps, NETWORK_MAP, COMPUTE_MAP, VOLUME_MAP

cloudentry_id = "yacmp:cloudentry:type:generic-cloud:zstack"
Orchestra_Maps(cloudentry_id, Network, NETWORK_MAP)
Orchestra_Maps(cloudentry_id, Compute, COMPUTE_MAP)
Orchestra_Maps(cloudentry_id, Volume, VOLUME_MAP)
