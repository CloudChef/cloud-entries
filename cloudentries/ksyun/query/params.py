# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import ParamType, BasicSchema, ConvertParams


class KsyunConvertParams(ConvertParams):

    def __init__(self, raw_params):
        super(KsyunConvertParams, self).__init__(raw_params)
        self.filters = {}

    def convert(self, param_format):
        converted_params = {}
        for converted_key, param_schema in list(param_format.items()):
            if self.ksyun_filter_params(param_schema):
                continue
            param_value = self.fixed_value(converted_key, param_schema)
            if not param_value:
                _raw_key = self.raw_key(param_schema)
                param_value = self.param_value(param_schema)
                self.validate_required(param_schema, _raw_key, param_value, "Convert Param")
                self.validate_type(param_schema, _raw_key, param_value, "Convert Param")
                self.validate_allow_values(param_schema, _raw_key, param_value, "Convert Param")
                param_value = self.filter_param(converted_key, param_schema)
            if param_value:  # remove params with empty value
                converted_params.update(param_value)
        filter_params = self.generate_filters()
        if filter_params:
            converted_params.update(filter_params)
        return converted_params

    def ksyun_filter_params(self, param_schema):
        filter_name = param_schema.get('filter_name')
        self.filter_key = param_schema.get('filter_key')
        param_value = self.param_value(param_schema)
        if filter_name and param_value:
            if filter_name not in self.filters:
                self.filters.update({filter_name: param_value.split(",")})
            self.filters[filter_name].append(param_value)
        return filter_name

    def generate_filters(self):
        """
        generate filter params, format like:
        {"Subnet.1.Name": "zone",
        "Subnet.1.Value.1": "shanghai-1",
        "Subnet.1.Value.2": "shanghai-2",
        }
        """
        filter_param = {}
        key_index = 1
        for filter_name, values in list(self.filters.items()):
            filter_name_key = "Filter.{}.Name".format(key_index)
            filter_param.update({
                filter_name_key: filter_name
            })
            for value_index, value in enumerate(values):
                filter_value_key = "Filter.{}.Value.{}".format(key_index, value_index + 1)
                filter_param.update({
                    filter_value_key: value
                })
            key_index += 1
        return filter_param

    def filter_param(self, converted_key, param_schema):
        """
        generate filter params, format like: {"Subnet.1": "123"}
        """
        _filter_key = param_schema.get("filter_key")
        param_value = self.param_value(param_schema)
        if not _filter_key:
            if param_value:
                return {converted_key: param_value}
            return {}
        param_value = param_value if param_value else self.raw_params.get('resource_id')
        filterd_resources = {}
        if param_value:
            resource_ids = param_value.split(',')
            for index, resource_id in enumerate(resource_ids):
                host_key = "{}.{}".format(_filter_key, index + 1)
                filterd_resources.update({
                    host_key: resource_id
                })

        return filterd_resources


class ZoneDesc(object):
    Schema = {
        "region": BasicSchema.schema(raw_key="region", required=False, param_type=ParamType.String)
    }


class ImageDesc(object):
    Schema = {
        "ImageId": BasicSchema.schema(raw_key="resource_id", required=False, param_type=ParamType.String),
    }


class InstanceDesc(object):
    Schema = {
        "MaxResults": BasicSchema.schema(raw_key="MaxResults", required=False, value=1000),
        "InstanceId": BasicSchema.schema(raw_key="resource_id", filter_key="InstanceId"),
    }


class FlavorDesc(object):
    Schema = {
        "instance-family": BasicSchema.filter_schema(raw_key="familyId", filter_name="instance-family"),
        "instance-type": BasicSchema.filter_schema(raw_key="instanceType", filter_name="instance-type"),
        "availability-zone": BasicSchema.filter_schema(raw_key="zone", filter_name="availability-zone")
    }


class LocalVolumeDesc(object):
    Schema = {
        "LocalVolumeId": BasicSchema.schema(raw_key="resource_id", required=False),
        "InstanceId": BasicSchema.schema(raw_key="InstanceId", required=False),
        "LocalVolumeCategory": BasicSchema.schema(raw_key="volume_category", required=False)
    }


class CloudVolumeDesc(object):
    Schema = {
        "VolumeId": BasicSchema.filter_schema(raw_key="resource_id", filter_name="VolumeId"),
        "VolumeCategory": BasicSchema.schema(raw_key="volume_category", required=False),
    }


class InstanceVolumeDesc(object):
    Schema = {
        "InstanceId": BasicSchema.schema(raw_key="InstanceId", required=True)
    }


class LocalVolumeSnapshotDesc(object):
    Schema = {
        "SourceLocalVolumeId": BasicSchema.schema(raw_key="VolumeId", required=False),
        "LocalVolumeSnapshotId": BasicSchema.schema(raw_key="resource_id", required=False),
        "LocalVolumeSnapshotCount": BasicSchema.schema(raw_key="LocalVolumeSnapshotCount", value=1000)

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
        "VolumeId": BasicSchema.schema(raw_key="VolumeId", required=True, param_type=ParamType.String),
        "SnapshotId": BasicSchema.schema(raw_key="resource_id", required=False, param_type=ParamType.String),
        "MaxResults": BasicSchema.schema(raw_key="MaxResults", value=1000)
    }


class VpcDesc(object):
    Schema = {
        "VpcId": BasicSchema.schema(raw_key="resource_id", filter_key="VpcId")
    }


class SubnetDesc(object):
    Schema = {
        "subnet-type": BasicSchema.filter_schema(raw_key="SubnetType", filter_name='subnet-type'),
        "vpc-id": BasicSchema.filter_schema(raw_key="vpcId", filter_name='vpc-id'),
        "SubnetId": BasicSchema.schema(raw_key="resource_id", filter_key="SubnetId")
    }


class FirewallDesc(object):
    Schema = {
        "SecurityGroupId": BasicSchema.schema(raw_key="resource_id", required=False, filter_key='SecurityGroupId'),
        "vpc-id": BasicSchema.filter_schema(raw_key="vpcId", filter_name='vpc-id')
    }


class EipDesc(object):
    Schema = {
        "AllocationId": BasicSchema.schema(raw_key="resource_id", required=False, filter_key='AllocationId')
    }


class LbListenerDesc(object):
    Schema = {
        "State": BasicSchema.schema(raw_key="State", required=False, param_type=ParamType.String),
        "load-balancer-id": BasicSchema.filter_schema(raw_key="loadbalancerId", filter_name='load-balancer-id')
    }
