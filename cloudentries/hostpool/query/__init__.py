# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.utils import Platforms
from .client import HostClient
cloudentry_id = "yacmp:cloudentry:type:hostpool"

Platforms(cloudentry_id, HostClient)
