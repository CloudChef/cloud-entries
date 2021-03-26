# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from functools import wraps
from .utils import BasicSchema, ParamType, CommonValidate


class CommonCloudResponse(CommonValidate):

    def __init__(self, raw_resp):
        super(CommonCloudResponse, self).__init__(raw_resp)

    def response(self, resp_format):
        _resp = []
        for resp in self.raw_params:
            each_resp = {}
            for param_key, param_schema in list(resp_format[0].items()):
                param_value = resp.get(param_key) if resp.get(param_key) else ""
                self.validate_required(param_schema, param_key, param_value, "Response")
                self.validate_type(param_schema, param_key, param_value, "Response")
                if param_value:  # value 为空时，不返回对应key
                    each_resp.update({
                        param_key: param_value
                    })
            _resp.append(each_resp)
        return _resp


def common_response(response_schema, validate_method=CommonCloudResponse):
    """
    validate_method: Validate the `resp` received from each cloud platform
                     whether match `response_schema` or not
    """

    def validate_resp(func):
        @wraps(func)
        def wrapper(self):
            resp = func(self)
            _response = validate_method(resp).response(response_schema)
            return _response

        return wrapper

    return validate_resp


class FilterResponse(object):

    @classmethod
    def filter_resource(cls, params, resp):
        """
        Filter one or multi resource(s) according to resource_id, use at: params doesn't support filter
        """
        if not params.get('resource_id'):
            return resp
        aim = []
        resource_ids = params.get('resource_id').split(',')
        for dct in resp:
            if dct['Id'] in resource_ids:
                aim.append(dct)
        return aim

    @classmethod
    def filter_image_name(cls, params, resp):
        """
        Filter one or multi resource(s) according to resource_id, use at: params doesn't support filter
        """
        pattern_image_name = params.get('patternImageName')
        if not pattern_image_name:
            return resp
        aim = []
        for dct in resp:
            if pattern_image_name.lower() in dct['Name'].lower():
                aim.append(dct)
        return aim

    @classmethod
    def filter_flavor(cls, params, resp):
        """
        Filter one or multi resource(s) according to resource_id, use at: params doesn't support filter
        """
        is_filter = params.get('matchCpuAndMemory')
        if (not is_filter) or str(is_filter).lower() != "true":
            return resp
        aim = []
        _cpu = params.get('cpu')
        _mem = params.get('memory')
        for dct in resp:
            cpu, mem = str(dct['CPU']), str(dct['Memory'])
            if _cpu and cpu != str(_cpu):
                continue
            if _mem and mem != str(_mem):
                continue
            aim.append(dct)
        return aim

    @classmethod
    def filter_os_type(cls, params, resp):
        """
        filter one or multi region(s) according to region
        """
        os_type = params.get('osType')
        if (not os_type) or (not resp):
            return resp
        linux_images, windows_images = [], []
        for image in resp:
            if 'windows' in image.get('Platform', '').lower():
                windows_images.append(image)
            else:
                linux_images.append(image)
        return windows_images if os_type.lower() == 'windows' else linux_images


def convert_response(resp_convert_schema):
    """
    Decorate class `BasicClient`'s method, and convert each cloud platform's response according to `resp_convert_schema`
    """

    def validate_response(func):
        @wraps(func)
        def wrapper(self, params=None):
            resp = func(self, params)
            return resp_convert_schema(resp)

        return wrapper

    return validate_response


def filter_output(validate_method):
    """
    Decorate class `BasicClient`'s method, and filter response's resource
    """

    def validate_response(func):
        @wraps(func)
        def wrapper(self):
            resp = func(self)
            return validate_method(self.query_params, resp)

        return wrapper

    return validate_response


class Validation(object):
    Schema = [{
        "Id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "IsDefault": BasicSchema.schema(required=False, param_type=ParamType.Bool)
    }]


class Region(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "IsDefault": BasicSchema.schema(required=False, param_type=ParamType.Bool)
    }]


class Zone(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Region": BasicSchema.schema(required=False, param_type=ParamType.String),
        "RegionId": BasicSchema.schema(required=False),
        "RegionName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "IsDefault": BasicSchema.schema(required=False, param_type=ParamType.Bool)
    }]


class Image(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "State": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageDescription": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageSize": BasicSchema.schema(required=False),
        "Features": BasicSchema.schema(required=False, param_type=ParamType.List),
        "Platform": BasicSchema.schema(required=False),
        "OsType": BasicSchema.schema(required=False, param_type=ParamType.String)
    }]


class Instance(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Status": BasicSchema.schema(required=True, param_type=ParamType.String),
        "PowerState": BasicSchema.schema(required=False, param_type=ParamType.String),
        "OsType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "OsName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "State": BasicSchema.schema(required=False, param_type=ParamType.String),
        "NetworkState": BasicSchema.schema(required=False, param_type=ParamType.String),
        "HostType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "StorageType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "DiskSet": BasicSchema.schema(required=False, param_type=ParamType.List),
        "IPSet": BasicSchema.schema(required=False, param_type=ParamType.List),
        "SubnetType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ChargeType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ExpireTime": BasicSchema.schema(required=False),
        "CreateTime": BasicSchema.schema(required=False),
        "CPU": BasicSchema.schema(required=False),
        "GPU": BasicSchema.schema(required=False),
        "Memory": BasicSchema.schema(required=False),
        "IPv6Feature": BasicSchema.schema(required=False),
        "MachineType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "OperatingSystem": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Uuid": BasicSchema.schema(required=False),
        "Storage": BasicSchema.schema(required=False),
        "NetworkAddress": BasicSchema.schema(required=False),
        "Placement": BasicSchema.schema(required=False),
        "PrivateIpAddress": BasicSchema.schema(required=False),
        "PublicIpAddress": BasicSchema.schema(required=False),
        "PrivateIpAddresses": BasicSchema.schema(required=False),
        "PublicIpAddresses": BasicSchema.schema(required=False),
        "DataDisks": BasicSchema.schema(required=False),
        "SystemDisk": BasicSchema.schema(required=False),
        "VirtualPrivateCloud": BasicSchema.schema(required=False),
        "InstanceType": BasicSchema.schema(required=False),
        "HostName": BasicSchema.schema(required=False),
        "SecurityGroupIds": BasicSchema.schema(required=False),
        "Tags": BasicSchema.schema(required=False)
    }]


class Volume(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Status": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "SnapshotCount": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "SnapEnable": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "Size": BasicSchema.schema(required=False),
        "IsExpire": BasicSchema.schema(required=False, param_type=ParamType.String),
        "IsBoot": BasicSchema.schema(required=False),
        "ExpiredTime": BasicSchema.schema(required=False),
        "DiskType": BasicSchema.schema(required=True, param_type=ParamType.String),
        "DeviceName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "CreateTime": BasicSchema.schema(required=False),
        "CloneEnable": BasicSchema.schema(required=False),
        "ChargeType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "BackupMode": BasicSchema.schema(required=False, param_type=ParamType.String),
        "HostIP": BasicSchema.schema(required=False, param_type=ParamType.String),
        "HostId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "HostName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ImageId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Version": BasicSchema.schema(required=False),
        "Category": BasicSchema.schema(required=True),
        "Local": BasicSchema.schema(required=False),
        "InstanceId": BasicSchema.schema(required=False),
        "InstanceName": BasicSchema.schema(required=False),
        "DiskUsage": BasicSchema.schema(required=False),
        "Attachment": BasicSchema.schema(required=False)
    }]


class VolumeType(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String)
    }]


class Snapshot(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Size": BasicSchema.schema(required=False),
        "Status": BasicSchema.schema(required=True, param_type=ParamType.String),
        "VolumeId": BasicSchema.schema(required=False),
        "VolumeName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "VolumeStatus": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ExpiredTime": BasicSchema.schema(required=False, param_type=ParamType.String),
        "DiskType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ChargeType": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Description": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Version": BasicSchema.schema(required=False)
    }]


class Vpc(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Network": BasicSchema.schema(required=False, param_type=ParamType.List),
        "Cidr": BasicSchema.schema(required=False),
        "SubnetCount": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "IPv6Network": BasicSchema.schema(required=False, param_type=ParamType.String),
        "HostsAssociated": BasicSchema.schema(required=False),
        "HostsInitialized": BasicSchema.schema(required=False),
        "VlansCount": BasicSchema.schema(required=False),
        "Usage": BasicSchema.schema(required=False),
        "Type": BasicSchema.schema(required=False),
        "BondMode": BasicSchema.schema(required=False),
        "BondName": BasicSchema.schema(required=False),
        "description": BasicSchema.schema(required=False),
        "Zone": BasicSchema.schema(required=False),
        "Status": BasicSchema.schema(required=False),
        "vmNics": BasicSchema.schema(required=False),

    }]


class Subnet(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Network": BasicSchema.schema(required=False),
        "Cidr": BasicSchema.schema(required=False),
        "Netmask": BasicSchema.schema(required=False),
        "Gateway": BasicSchema.schema(required=False),
        "RouteTableId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Type": BasicSchema.schema(required=False),
        "NetworkId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "VPCName": BasicSchema.schema(required=False, param_type=ParamType.String),
        "VRouterId": BasicSchema.schema(required=False),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "dns": BasicSchema.schema(required=False),
        "hostRoute": BasicSchema.schema(required=False),
        "ipRanges": BasicSchema.schema(required=False),
        "category": BasicSchema.schema(required=False),
        "CreateTime": BasicSchema.schema(required=False),
        "Status": BasicSchema.schema(required=False)
    }]


class Firewall(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "GroupId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "ResourceCount": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "Rule": BasicSchema.schema(required=False, param_type=ParamType.List),
        "Type": BasicSchema.schema(required=False, param_type=ParamType.String),
        "SecurityGroupDesc": BasicSchema.schema(required=False, param_type=ParamType.String),
        "attachedL3NetworkUuids": BasicSchema.schema(required=False),
        "VpcId": BasicSchema.schema(required=False),
        "CreateTime": BasicSchema.schema(required=False)
    }]


class Eip(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "State": BasicSchema.schema(required=True, param_type=ParamType.String),
        "PublicIp": BasicSchema.schema(required=False, param_type=ParamType.String),
        "LineId": BasicSchema.schema(required=False, param_type=ParamType.String),
        "BandWidth": BasicSchema.schema(required=False),
        "ChargeType": BasicSchema.schema(required=False),
        "CreateTime": BasicSchema.schema(required=False),
        "InstanceId": BasicSchema.schema(required=False),
        "InstanceType": BasicSchema.schema(required=False)
    }]


class Flavor(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "InstanceFamily": BasicSchema.schema(required=False, param_type=ParamType.String),
        "GPU": BasicSchema.schema(required=False),
        "CPU": BasicSchema.schema(required=False),
        "Memory": BasicSchema.schema(required=False),
        "type": BasicSchema.schema(required=False),
        "InstanceType": BasicSchema.schema(required=False, param_type=ParamType.String)
    }]


class Vlan(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "description": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Vlan": BasicSchema.schema(required=False),
        "Type": BasicSchema.schema(required=False)
    }]


class Vxlan(object):
    Schema = [{
        "Id": BasicSchema.schema(required=True, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "description": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Type": BasicSchema.schema(required=False, param_type=ParamType.Int),
    }]


class Family(object):
    Schema = [{
        "Id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Zone": BasicSchema.schema(required=False, param_type=ParamType.String),
        "description": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Type": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "AvailabilityZoneSet": BasicSchema.schema(required=False)
    }]


class Line(object):
    Schema = [{
        "Name": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "IpVersion": BasicSchema.schema(required=False, param_type=ParamType.String),
        "LineType": BasicSchema.schema(required=False)
    }]


class LbListener(object):
    Schema = [{
        "Id": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Name": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Protocol": BasicSchema.schema(required=False, param_type=ParamType.String),
        "Port": BasicSchema.schema(required=False),
        "Method": BasicSchema.schema(required=False, param_type=ParamType.String),
        "SessionState": BasicSchema.schema(required=False, param_type=ParamType.String),
        "BackendNum": BasicSchema.schema(required=False, param_type=ParamType.Int),
        "RealServer": BasicSchema.schema(required=False, param_type=ParamType.List)
    }]


class Balance(object):
    Schema = [{
        "Balance": BasicSchema.schema(required=False, param_type=ParamType.Int),
    }]
