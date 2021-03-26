# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import BasicSchema


class VolumeDesc(object):
    Schema = {
        "InstanceId": BasicSchema.schema(raw_key="InstanceId", required=True)
    }
