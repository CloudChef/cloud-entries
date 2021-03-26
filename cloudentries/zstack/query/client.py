from cloudchef_integration.tasks.cloud_resources.commoncloud.params import ParamType, BasicSchema, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from .connection import ZStackConnection
from .params import ImageDesc, SubnetDesc
from .response import ZstackStandardResponse


class ZstackConnectionDesc:
    Schema = {
        "username": BasicSchema.schema(raw_key="username", required=True, param_type=ParamType.String),
        "password": BasicSchema.schema(raw_key="password", required=True, param_type=ParamType.String),
        "url": BasicSchema.schema(raw_key="url", required=True, param_type=ParamType.String),
    }


class ZstackClient:
    def __init__(self, connection_config):
        self.connection_config = connection_config
        self.conn = self.get_conn()

    def get_conn(self):
        username = self.connection_config.get("username")
        password = self.connection_config.get("password")
        url = self.connection_config.get("url")
        return ZStackConnection(username, password, url)

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.instance)
    def describe_vm(self, query_params):
        endpoint = '/vm-instances'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(ImageDesc.Schema)
    @convert_response(ZstackStandardResponse.image)
    def describe_image(self, query_params):
        endpoint = '/images'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.flavor)
    def describe_flavor(self, query_params):
        endpoint = '/instance-offerings'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.volume)
    def describe_volume(self, query_params):
        endpoint = '/volumes'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.snapshot)
    def describe_snapshot(self, query_params):
        endpoint = '/volume-snapshots'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.vlan)
    def describe_vlan(self, query_params):
        endpoint = '/l2-networks/vlan'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(SubnetDesc.Schema)
    @convert_response(ZstackStandardResponse.subnet)
    def describe_subnet(self, query_params):
        endpoint = '/l3-networks'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.vpc)
    def describe_vpc(self, query_params):
        endpoint = '/vpc/virtual-routers'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.securitygroup)
    def describe_security_group(self, query_params):
        endpoint = '/security-groups'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.vxlan)
    def describe_vxlan(self, query_params):
        endpoint = '/l2-networks/vxlan'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()

    @convert_params(EmptyDesc.Schema)
    @convert_response(ZstackStandardResponse.volume_type)
    def describe_volume_type(self, query_params):
        endpoint = '/disk-offerings'
        response = self.conn.call(method='get', endpoint=endpoint, condition=query_params)
        return response.json()
