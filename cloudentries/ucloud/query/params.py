# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import ParamType, BasicSchema


class RegionDesc(object):
    Schema = {}


class ImageDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String),
        # UCloud只支持单个Zone过滤，后续如果有需要，可查询多次后返回,或自定义filter。
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "ImageType": BasicSchema.schema(raw_key="ImageType", required=False, param_type=ParamType.String),
        "OsType": BasicSchema.schema(raw_key="osType", required=False, param_type=ParamType.String),
        "ImageId": BasicSchema.schema(raw_key="ImageId", required=False, param_type=ParamType.String),
    }


class InstanceDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(raw_key="zone", required=True, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "UHostIds": BasicSchema.schema(raw_key="resource_id", required=False, param_type=ParamType.String,
                                       filter_key="UHostIds")
    }


class DiskDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "UDiskId": BasicSchema.schema(raw_key="UDiskId", required=False, param_type=ParamType.String),
        "DiskType": BasicSchema.schema(raw_key="DiskType", required=False, param_type=ParamType.String)
    }


class SnapshotDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "UDiskId": BasicSchema.schema(raw_key="UDiskId", required=False, param_type=ParamType.String),
        "SnapshotId": BasicSchema.schema(raw_key="SnapshotId", required=False, param_type=ParamType.String),
    }


class VpcDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String)
    }


class SubnetDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "SubnetId": BasicSchema.schema(raw_key="SubnetId", required=False, param_type=ParamType.String),
        "VPCId": BasicSchema.schema(raw_key="VPCId", required=False, param_type=ParamType.String)
    }


class FirewallDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String),
        "FWId": BasicSchema.schema(raw_key="FWId", required=False, param_type=ParamType.String),
        "ResourceId": BasicSchema.schema(raw_key="ResourceId", required=False, param_type=ParamType.String),
        "ResourceType": BasicSchema.schema(raw_key="ResourceType", required=False, param_type=ParamType.String)
    }


class EipDesc(object):
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "ProjectId": BasicSchema.schema(raw_key="ProjectId", required=False, param_type=ParamType.String)
    }
