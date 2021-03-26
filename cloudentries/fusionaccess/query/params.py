# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import ParamType, BasicSchema


class RegionDesc(object):
    Schema = {}


class ClusterDesc(object):
    Schema = {
        "siteId": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
    }


class TemplateDesc(object):
    Schema = {
        "siteId": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "clusterId": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String),
    }


class DatastoreDesc(object):
    Schema = {
        "siteId": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "clusterId": BasicSchema.schema(raw_key="zone", required=True, param_type=ParamType.String),
    }


class DatastoreTemplateDesc(object):
    Schema = {
        "siteID": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "templateID": BasicSchema.schema(raw_key="instanceType", required=True, param_type=ParamType.String),
        "clusterID": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String),
    }


class SecuritygroupDesc(object):
    Schema = {
        "siteId": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String)
    }


class PortgroupDesc(object):
    Schema = {
        "siteId": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "clusterId": BasicSchema.schema(raw_key="zone", required=False, param_type=ParamType.String)
    }


class InstanceDesc(object):  # not use,just a example
    Schema = {
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "param": BasicSchema.schema(required=True, param_type=ParamType.Dict)
    }
