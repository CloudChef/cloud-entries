# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.params import ParamType, BasicSchema, ConvertParams


class TencentConvertParams(ConvertParams):

    def __init__(self, raw_params):
        super(TencentConvertParams, self).__init__(raw_params)
        self.filters = {}
        self.filter_key = ""

    def convert(self, param_format):
        converted_params = {}
        for converted_key, param_schema in list(param_format.items()):
            if self.tc_filter_params(param_schema):
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
            converted_params.update({
                "Filters": filter_params
            })
        return converted_params

    def tc_filter_params(self, param_schema):
        filter_name = param_schema.get('filter_name')
        self.filter_key = param_schema.get('filter_key')
        param_value = self.param_value(param_schema)
        if filter_name and param_value:
            if filter_name == "tags":
                self._filter_tags(param_value)
            else:
                if filter_name not in self.filters:
                    self.filters.update({filter_name: []})
                self.filters[filter_name].extend(param_value.split(','))

        return filter_name

    def _filter_tags(self, param_value):
        tag_filters = {}
        for tag in param_value:
            filter_tag_key = "tag:{}".format(tag.get("labelKey"))
            if filter_tag_key not in tag_filters:
                tag_filters.update({filter_tag_key: [tag.get("labelValue")]})
            else:
                tag_filters[filter_tag_key].append(tag.get("labelValue"))
        self.filters.update(tag_filters)

    def generate_filters(self):
        filter_param = []
        for filter_name, values in list(self.filters.items()):
            filter_param.append({
                "Name": filter_name,
                "Values": values
            })
        return filter_param


class ImageDesc(object):
    Schema = {
        "image-id": BasicSchema.filter_schema(raw_key="resource_id", filter_name="image-id"),
        "Limit": BasicSchema.schema(raw_key="Limit", value=100)
    }


class InstanceDesc(object):
    Schema = {
        "zone": BasicSchema.filter_schema(raw_key="zone", filter_name="zone"),
        "instance-id": BasicSchema.filter_schema(raw_key="resource_id", filter_name="instance-id"),
        "instance-name": BasicSchema.filter_schema(raw_key="name", filter_name="instance-name"),
        "tags": BasicSchema.filter_schema(raw_key="tags", filter_name="tags"),
        "Limit": BasicSchema.schema(raw_key="Limit", value=100),
        "Offset": BasicSchema.schema(raw_key="Offset", param_type=ParamType.Int)
    }


class DiskDesc(object):
    Schema = {
        "instance-id": BasicSchema.filter_schema(raw_key="InstanceId", filter_name="instance-id"),
        "disk-id": BasicSchema.filter_schema(raw_key="resource_id", filter_name="disk-id")
    }


class SnapshotDesc(object):
    Schema = {
        "InstanceIds": BasicSchema.schema(raw_key="InstanceId", required=True, param_type=ParamType.String)
    }


class NetworkDesc(object):
    Schema = {
        "vpc-id": BasicSchema.filter_schema(raw_key="resource_id", filter_name="vpc-id")
    }


class FlavorDesc(object):
    Schema = {
        "zone": BasicSchema.filter_schema(raw_key="zone", filter_name="zone")
    }


class VncDesc(object):
    Schema = {
        "InstanceId": BasicSchema.schema(raw_key="InstanceId", required=False, param_type=ParamType.String),
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String)
    }


class SubnetDesc(object):
    Schema = {
        "zone": BasicSchema.filter_schema(raw_key="zone", filter_name="zone"),
        "subnet-id": BasicSchema.filter_schema(raw_key="resource_id", filter_name="subnet-id")
    }


class SecurityGroupDesc(object):
    Schema = {
        "SecurityGroupIds": BasicSchema.schema(raw_key="resource_id", required=False, filter_key="SecurityGroupIds")
    }


class VolumeTypeDesc(object):
    Schema = {
        "InquiryType": BasicSchema.schema(raw_key="InquiryType ", value="INQUIRY_CVM_CONFIG"),
        "DiskChargeType": BasicSchema.schema(raw_key="DiskChargeType ", value="POSTPAID_BY_HOUR"),
        "Region": BasicSchema.schema(raw_key="region", required=True, param_type=ParamType.String),
        "Zones": BasicSchema.schema(raw_key="zone", required=False, filter_key="Zones"),
        "InstanceFamilies": BasicSchema.schema(raw_key="instance_family", filter_key="InstanceFamilies"),
        "DiskUsage": BasicSchema.schema(raw_key="disk_usage", allow_values=["DATA_DISK", "SYSTEM_DISK"])
    }


class BalanceDesc(object):
    Schema = {

    }
