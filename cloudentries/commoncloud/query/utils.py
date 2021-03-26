# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from functools import wraps
import datetime
import re
from .constants import InstanceStatusMapper, PowerStatusMapper


class ParamType(object):
    """
    Design the type of param, the right should be equal with the value of type(param) in python
    """
    String = "str"
    Int = "int"
    Dict = "dict"
    List = "list"
    Tuple = "tuple"
    Bool = "bool"


class BasicSchema(object):

    @staticmethod
    def schema(raw_key="", required=False, param_type="", allow_values=None, filter_key="", value=""):
        """
        raw_key: `Optional`; the param name received from CMP
        required: `Optional`; validate the param is (not) required; value: True | False
        param_type: `Optional`; validate the type of the Param; value: property of class `ParamType`
        allow_values: `Optional`;validate the param value in allow_values if param value and allow_values are not empty
        value: `Optional`; if this param is not empty, use the value directly without above validation
        filter_key: `Optional`; generate filter params; value: "UHostIds"
        """
        return {
            "raw_key": raw_key,
            "required": required,
            "type": param_type,
            "allow_values": allow_values,
            "filter_key": filter_key,
            "value": value
        }

    @staticmethod
    def filter_schema(raw_key="", filter_name=""):
        return {
            "raw_key": raw_key,
            "filter_name": filter_name
        }


class ValidatException(Exception):

    def __init__(self, param_name, handle_type="", msg=""):
        self.param_name = param_name
        self.msg = msg
        self.handle_type = handle_type

    def __str__(self):
        return "{}:`{}` Validate failed, reason:{}".format(self.handle_type, self.param_name, self.msg)


class CommonValidate(object):

    def __init__(self, raw_params):
        self.raw_params = raw_params

    def param_value(self, param_key):
        param_value = self.raw_params.get(param_key, "")
        return param_value

    @staticmethod
    def validate_required(param_schema, param_key, param_value, handle_type="Param"):
        _required = param_schema.get("required")
        if _required and (not param_value):
            err_msg = "param `{}` is required, but received is empty".format(param_key)
            raise ValidatException(param_key, handle_type, err_msg)

    @staticmethod
    def validate_type(param_schema, param_key, param_value, handle_type="Param"):
        _type = param_schema.get("type")
        if _type and param_value and (type(param_value).__name__ != _type):
            err_msg = "the type of: {} should be: {}, but the given is: {}".format(param_key, _type, type(param_value))
            raise ValidatException(param_key, handle_type, err_msg)

    @staticmethod
    def validate_allow_values(param_schema, param_key, param_value, handle_type="Param"):
        _allow_values = param_schema.get("allow_values")
        if _allow_values and param_value and (param_value not in _allow_values):
            err_msg = "the allow values of: {} should in: {}, but the given is: {}".format(param_key,
                                                                                           _allow_values, param_value)
            raise ValidatException(param_key, handle_type, err_msg)


def support_getattr(cls):
    """
    In order to be compatible with the old method of CommonCloud Resource Query method
    """

    class wrapper():
        def __init__(self, *args, **kwargs):
            self.wrapped = cls(*args, **kwargs)

        def __getattr__(self, name):
            try:
                return getattr(self.wrapped, name)()
            except TypeError as e:
                if "not callable" in str(e):
                    return getattr(self.wrapped, name)
    return wrapper


def standardize_obj(obj, mapper):
    standard_obj = {}
    for key in obj:
        if key in mapper:
            standard_obj[mapper[key]] = obj[key]
        else:
            standard_obj[key] = obj[key]
    return standard_obj


def patch_key(resp, mapper):
    return [standardize_obj(obj, mapper) for obj in resp]


def utctime_to_localtime(utc_time, time_delta=0):
    utc_format = "%Y-%m-%dT%H:%M:%SZ"
    local_time = datetime.datetime.strptime(utc_time, utc_format)
    if time_delta:
        local_time = local_time + datetime.timedelta(hours=time_delta)
    else:
        # ksyun: utc_time=local_time
        local_time = local_time
    return local_time


# transfer vm status to standard format
def format_ins_status(raw_status, default_status="unknown"):
    for status, raw_lst in list(InstanceStatusMapper.items()):
        if raw_status.lower() in raw_lst:
            return status
    return default_status


# transfer vm power status to standard format
def format_power_status(raw_status, default_status="SUSPENDED"):
    for status, raw_lst in list(PowerStatusMapper.items()):
        if raw_status.lower() in raw_lst:
            return status
    return default_status


def filter_flavor(resp, query_params, by_name=False):
    """
    根据cpu/memory过滤flavor
    """
    is_filter = query_params.get('matchCpuAndMemory')
    if is_filter and str(is_filter).lower() == "true":
        new_resp = []
        _cpu = query_params.get('cpu')
        _mem = query_params.get('memory')
        for each_flavor in resp:
            try:
                if by_name:  # eg: each_flavor["Name"] = "1C1G"
                    flavor_name = re.split("C|G", each_flavor["Name"])
                    cpu, mem = flavor_name[0], flavor_name[1]
                else:  # eg: each_flavor['CPU'] = 1  each_flavor['Memory'] = 1
                    cpu, mem = str(each_flavor['CPU']), str(each_flavor['Memory'])
                if _cpu and cpu != str(_cpu):
                    continue
                if _mem and mem != str(_mem):
                    continue
                new_resp.append(each_flavor)
            except Exception as error:
                raise Exception('Filter flavor resource by cpu&mem abnormal, query params:{}, flavor info:{}, error:{}'
                                .format(query_params, each_flavor, error))
        return new_resp
    return resp
