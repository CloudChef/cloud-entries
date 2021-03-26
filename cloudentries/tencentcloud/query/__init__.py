# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.utils import Platforms
from .resources import TencentResource
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

cloudentry_id = "yacmp:cloudentry:type:generic-cloud:tencentcloud"
Platforms(cloudentry_id, TencentResource)
