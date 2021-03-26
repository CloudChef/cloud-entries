# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import hashlib
import json
import sys

if sys.version_info.major == 2:
    # Python2
    import urllib.request
    import urllib.parse
    import urllib.error
    import urllib.parse
    import http.client
else:
    # Python3
    import urllib.request
    import urllib.parse
    import urllib.error
    import urllib.parse
    import http.client
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from cloudchef_integration.tasks.cloud_resources.ucloud.response import UcloudStandardResponse
from cloudchef_integration.tasks.cloud_resources.ucloud import params as UcloudParams


class UConnection(object):
    def __init__(self, base_url, public_key, private_key):
        self.base_url = base_url
        self.private_key = private_key
        self.public_key = {'PublicKey': public_key}
        if sys.version_info.major == 2:
            # Python2
            o = urllib.parse.urlsplit(base_url)
            if o.scheme == 'https':
                self.conn = http.client.HTTPSConnection(o.netloc)
            else:
                self.conn = http.client.HTTPConnection(o.netloc)
        else:
            # Python3
            o = urllib.parse.urlsplit(base_url)
            if o.scheme == 'https':
                self.conn = http.client.HTTPSConnection(o.netloc)
            else:
                self.conn = http.client.HTTPConnection(o.netloc)

    def __del__(self):
        self.conn.close()

    def verify_ac(self, params):
        _params = dict(self.public_key, **params)
        items = sorted(_params.items())

        params_data = ""
        for key, value in items:
            params_data = params_data + str(key) + str(value)

        params_data = params_data + self.private_key

        '''use sha1 to encode keys'''
        hash_new = hashlib.sha1()
        hash_new.update(params_data.encode('utf-8'))
        _params['Signature'] = hash_new.hexdigest()

        return _params

    def get(self, uri, params):
        _params = self.verify_ac(params)
        if sys.version_info.major == 2:
            # Python2
            uri += "?" + urllib.parse.urlencode(_params)
        else:
            # Python3
            uri += "?" + urllib.parse.urlencode(_params, encoding='utf-8')

        self.conn.request("GET", uri)
        response = json.loads(self.conn.getresponse().read())
        return response

    def post(self, uri, params):
        _params = self.verify_ac(params)
        headers = {"Content-Type": "application/json"}
        self.conn.request("POST", uri, json.JSONEncoder().encode(_params), headers)
        response = json.loads(self.conn.getresponse().read())
        return response


class UcloudClient(object):
    def __init__(self, base_url, public_key, private_key, region):
        self.region = region
        self.conn = UConnection(base_url, public_key, private_key)

    @convert_params(UcloudParams.RegionDesc.Schema)
    @convert_response(UcloudStandardResponse.validation)
    def validation(self, params):
        params['Action'] = 'GetRegion'
        return self.conn.get('/', params)

    @convert_params(UcloudParams.RegionDesc.Schema)
    @convert_response(UcloudStandardResponse.region)
    def describe_region(self, params):
        params['Action'] = 'GetRegion'
        return self.conn.get('/', params)

    @convert_params(UcloudParams.RegionDesc.Schema)
    @convert_response(UcloudStandardResponse.zone)
    def describe_zone(self, params):
        params['Action'] = 'GetRegion'
        return self.conn.get('/', params)

    @convert_params(UcloudParams.ImageDesc.Schema)
    @convert_response(UcloudStandardResponse.image)
    def describe_image(self, params):
        params['Action'] = 'DescribeImage'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_params(UcloudParams.InstanceDesc.Schema)
    @convert_response(UcloudStandardResponse.instance)
    def describe_uhost(self, params):
        params['Action'] = 'DescribeUHostInstance'
        params['Region'] = self.region
        zones = params.get('Zone', '').split(',')
        resp = []
        for zone in zones:
            params['Zone'] = zone
            ret = self.conn.get('/', params).get('UHostSet', [])
            if ret:
                resp.extend(ret)
        return resp

    @convert_params(UcloudParams.SnapshotDesc.Schema)
    @convert_response(UcloudStandardResponse.snapshot)
    def describe_snapshot(self, params):
        params['Action'] = 'DescribeUDiskSnapshot'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_response(UcloudStandardResponse.volume_type)
    def volume_type(self, params):
        return []

    @convert_params(UcloudParams.DiskDesc.Schema)
    @convert_response(UcloudStandardResponse.volume)
    def describe_disk(self, params):
        params['Action'] = 'DescribeUDisk'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_params(UcloudParams.EipDesc.Schema)
    @convert_response(UcloudStandardResponse.eip)
    def describe_eip(self, params):
        params['Action'] = 'DescribeEIP'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_params(UcloudParams.FirewallDesc.Schema)
    @convert_response(UcloudStandardResponse.security_group)
    def describe_firewall(self, params):
        params['Action'] = 'DescribeFirewall'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_params(UcloudParams.SubnetDesc.Schema)
    @convert_response(UcloudStandardResponse.subnet)
    def describe_subnet(self, params):
        params['Action'] = 'DescribeSubnet'
        params['Region'] = self.region
        return self.conn.get('/', params)

    @convert_params(UcloudParams.VpcDesc.Schema)
    @convert_response(UcloudStandardResponse.network)
    def describe_vpc(self, params):
        params['Action'] = 'DescribeVPC'
        params['Region'] = self.region
        return self.conn.get('/', params)
