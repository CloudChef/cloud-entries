# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from kscore.session import get_session
from cloudchef_integration.tasks.cloud_resources.commoncloud.params import convert_params, EmptyDesc
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import convert_response
from cloudchef_integration.tasks.cloud_resources.ksyun import params as KsyunParams
from cloudchef_integration.tasks.cloud_resources.ksyun.response import KsyunStandardResponse


class KsyunConnection(object):
    def __init__(self, region=None, ks_access_key_id=None, ks_secret_access_key=None, domain=None, **kwargs):
        self.region = region
        self.ks_access_key_id = ks_access_key_id
        self.ks_secret_access_key = ks_secret_access_key
        self.domain = domain
        self.kwargs = kwargs

    def connection(self, service):
        try:
            session = get_session()
            if self.domain:
                session.set_domain(self.domain)
            client = session.create_client(service_name=service,
                                           region_name=self.region,
                                           ks_access_key_id=self.ks_access_key_id,
                                           ks_secret_access_key=self.ks_secret_access_key,
                                           use_ssl=False,
                                           **self.kwargs)
            return client
        except Exception as e:
            raise Exception("Connect to ksyun failed! the error message is {0}".format(e))


class KsyunClient(object):
    def __init__(self, region, ks_access_key_id, ks_secret_access_key, **kwargs):
        self.kc = KsyunConnection(region, ks_access_key_id, ks_secret_access_key, **kwargs)

    @convert_params(EmptyDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.region)
    def describe_region(self, params):
        client = self.kc.connection('kec')
        return client.describe_regions(**params)

    @convert_params(KsyunParams.ZoneDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.zone)
    def describe_availability_zone(self, params):
        client = self.kc.connection('kec')
        return client.describe_availability_zones(**params)

    @convert_params(KsyunParams.ImageDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.image)
    def describe_images(self, params):
        client = self.kc.connection('kec')
        return client.describe_images(**params)

    @convert_params(KsyunParams.InstanceDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.instance)
    def describe_instances(self, params):
        client = self.kc.connection('kec')
        return client.describe_instances(**params)

    @convert_params(KsyunParams.FlavorDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.flavor)
    def describe_flavor(self, params):
        client = self.kc.connection('kec')
        return client.describe_instance_type_configs(**params)

    @convert_params(KsyunParams.LocalVolumeDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.local_volume)
    def describe_local_volume(self, params):
        client = self.kc.connection('kec')
        return client.describe_local_volumes(**params)

    @convert_params(KsyunParams.LocalVolumeSnapshotDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.local_volume_sp)
    def describe_local_volume_snapshots(self, params):
        client = self.kc.connection('kec')
        return client.describe_local_volume_snapshots(**params).get('LocalVolumeSnapshotSet') or []

    @convert_params(EmptyDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.family)
    def describe_family(self, params):
        client = self.kc.connection('kec')
        return client.describe_instance_familys(**params)

    @convert_params(KsyunParams.VpcDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.network)
    def describe_vpcs(self, params):
        client = self.kc.connection('vpc')
        return client.describe_vpcs(**params)

    @convert_params(KsyunParams.SubnetDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.subnet)
    def describe_subnets(self, params):
        client = self.kc.connection('vpc')
        return client.describe_subnets(**params)

    @convert_params(KsyunParams.FirewallDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.security_group)
    def describe_security_groups(self, params):
        client = self.kc.connection('vpc')
        return client.describe_security_groups(**params)

    @convert_params(KsyunParams.EipDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.eip)
    def describe_addresses(self, params):
        client = self.kc.connection('eip')
        return client.describe_addresses(**params)

    @convert_params(EmptyDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.line)
    def get_lines(self, params):
        client = self.kc.connection('eip')
        return client.get_lines()

    @convert_params(KsyunParams.CloudVolumeDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.cloud_volume)
    def describe_volumes(self, params):
        client = self.kc.connection('ebs')
        return client.describe_volumes(**params)

    @convert_params(KsyunParams.InstanceVolumeDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.instance_volume)
    def describe_instance_volumes(self, params):
        client = self.kc.connection('ebs')
        return client.describe_instance_volumes(**params)

    @convert_params(KsyunParams.SnapshotDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.snapshot)
    def describe_snapshots(self, params):
        client = self.kc.connection('ebs')
        return client.describe_snapshots(**params)

    @convert_params(KsyunParams.LbListenerDesc.Schema, convert_method=KsyunParams.KsyunConvertParams)
    @convert_response(KsyunStandardResponse.lblistener)
    def describe_listeners(self, params):
        client = self.kc.connection('slb')
        return client.describe_listeners(**params)
