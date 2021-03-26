# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.utils import Platforms
from .resources import FusionAccessResource
cloudentry_id = "yacmp:cloudentry:type:generic-cloud:fusionaccess"

Platforms(cloudentry_id, FusionAccessResource)
