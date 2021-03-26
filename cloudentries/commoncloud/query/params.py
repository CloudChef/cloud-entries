# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from functools import wraps
from .utils import ParamType, BasicSchema, CommonValidate


class CommonCloudParams(CommonValidate):

    def __init__(self, raw_params):
        super(CommonCloudParams, self).__init__(raw_params)

    def params(self, param_format):
        validated_params = {}
        for param_key, param_schema in list(param_format.items()):
            param_value = self.param_value(param_key)
            self.validate_required(param_schema, param_key, param_value)
            self.validate_type(param_schema, param_key, param_value)
            self.validate_allow_values(param_schema, param_key, param_value)
            validated_params.update({param_key: param_value})
        return validated_params


def common_params(param_schema, validate_method=CommonCloudParams):
    """
    validate_method: Validate the `self.query_params` received from CMP (class `CloudResource`)
                     whether match `param_schema` or not
    """

    def validate_params(func):
        @wraps(func)
        def wrapper(self):
            converted_params = validate_method(self.query_params).params(param_schema)
            self.params = converted_params
            return func(self)

        return wrapper

    return validate_params


class ConvertParams(CommonValidate):

    def __init__(self, raw_params):
        super(ConvertParams, self).__init__(raw_params)

    def convert(self, param_format):
        converted_params = {}
        for converted_key, param_schema in list(param_format.items()):
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
        return converted_params

    def raw_key(self, param_schema):
        return param_schema.get("raw_key")

    def param_value(self, param_schema):
        _raw_key = param_schema.get("raw_key")
        param_value = self.raw_params.get(_raw_key, "")
        return param_value

    def fixed_value(self, converted_key, param_schema):
        _fixed = param_schema.get("value")
        # param_value = self.param_value(param_schema)
        if _fixed:
            return {converted_key: _fixed}

    def filter_param(self, converted_key, param_schema):
        """
        generate filter params, format like: {"UHosts.0": "123"}
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
                host_key = "{}.{}".format(_filter_key, index)
                filterd_resources.update({
                    host_key: resource_id
                })

        return filterd_resources


def convert_params(param_schema, convert_method=ConvertParams):
    """
    convert_method: Validate & Convert the params according to `param_schema`
                    to match each cloud platform's param format
    """

    def validate_params(func):
        @wraps(func)
        def wrapper(self, params=None):
            converted_params = convert_method(params).convert(param_schema)
            return func(self, converted_params)

        return wrapper

    return validate_params


class Region(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Validation(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Zone(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Image(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "osType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "patternImageName": BasicSchema.schema(required=False, param_type=ParamType.String)  # 根据image_name模糊匹配
    }


class Instance(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Volume(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "disk_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "disk_type": BasicSchema.schema(required=False, param_type=ParamType.String),
        "InstanceId": BasicSchema.schema(required=False, param_type=ParamType.String),
    }


class Snapshot(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "snapshot_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Vpc(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
    }


class Subnet(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "subnet_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "vpc_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Firewall(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "FWId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "resource_id": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Eip(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class Flavor(object):
    Schema = {
        "cpu": BasicSchema.schema(required=False),
        "memory": BasicSchema.schema(required=False),
        "matchCpuAndMemory": BasicSchema.schema(required=False, param_type=ParamType.Bool),
        "instanceType": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class LbListener(object):
    Schema = {
        "loadbalancerId": BasicSchema.schema(required=False, param_type=ParamType.String)
    }


class EmptyDesc(object):
    Schema = {

    }


class VolumeType(object):
    Schema = {
        "region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "instanceType": BasicSchema.schema(required=False, param_type=ParamType.String),
    }
