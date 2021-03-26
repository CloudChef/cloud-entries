# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.libs.fc_rest_client.client import FusionComputeClient as Client
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import patch_key, format_ins_status
from cloudchef_integration.tasks.cloud_resources.fusioncompute import constants


class FusionComputeClient(object):
    def __init__(self, connection_config, query_params=None):
        self.base_url = connection_config.get('base_url')
        self.username = connection_config.get('username')
        self.password = connection_config.get('password')
        self.site = connection_config.get('region')
        self.resource_id = query_params.get('resource_id')
        self.query_params = query_params
        self.client = Client(
            auth_url=self.base_url,
            username=self.username,
            password=self.password
        )

    @property
    def validation(self):
        return self.region

    @property
    def region(self):
        if self.resource_id:
            resp = [self.client.sites.get(self.resource_id)]
        else:
            resp = self.client.sites.list()['sites']
        return patch_key(resp, constants.REGION_MAPPER)

    @property
    def zone(self):
        if self.resource_id:
            resp = [self.client.hosts.get(self.resource_id)]
        else:
            resp = self.client.hosts.list(self.site)['hosts']
        return patch_key(resp, constants.ZONE_MAPPER)

    @property
    def instance(self):
        resp = []
        for index in range(100):
            offset = index * 100
            vms = self.client.servers.list(self.site, {"limit": 100, "offset": offset, "detail": 2})['vms']
            if not vms:
                break
            for vm in vms:
                if not vm.get('isTemplate'):
                    if self.resource_id and vm.get('urn') not in self.resource_id:
                        continue
                    vm["status"] = format_ins_status(vm["status"])
                    operate_system = ""
                    if vm.get("osOptions") and vm["osOptions"].get("osType"):
                        operate_system = vm["osOptions"].get("osType")
                    vm.update({
                        "OperatingSystem": operate_system
                    })
                    private_ip = [nic.get('ip') for nic in vm.get("vmConfig", {}).get("nics", {})]
                    vm.update({
                        "PrivateIpAddress": ",".join(private_ip),
                        "NetworkAddress": {
                            "PrivateIpAddress": ",".join(private_ip)
                        }
                    })
                    resp.append(vm)
        return patch_key(resp, constants.INSTANCE_MAPPER)

    @property
    def security_group(self):
        if self.resource_id:
            resp = [self.client.securitygroups.get(self.resource_id)]
        else:
            resp = self.client.securitygroups.list(self.site)['securityGroups']
        return patch_key(resp, constants.SECURITY_GROUP_MAPPER)

    @property
    def network(self):
        if self.resource_id:
            resp = [self.client.dvswitchs.get(self.resource_id)]
        else:
            resp = self.client.dvswitchs.list(self.site)['dvSwitchs']
        return patch_key(resp, constants.DVSWITCHS_MAPPER)

    @property
    def subnet(self):
        if self.resource_id:
            port_group = self.client.portgroups.get(self.resource_id)
            port_group['NetworkId'] = self.portgroup2dvswitch(self.resource_id)
            resp = [port_group]
        elif self.query_params.get('VpcId'):
            dvswitchs_urn = self.query_params.get('VpcId')
            resp = self.client.portgroups.list(dvswitchs_urn)['portGroups']
            for port_group in resp:
                port_group['NetworkId'] = dvswitchs_urn
        else:
            resp = []
            dvswitchs = self.client.dvswitchs.list(self.site)['dvSwitchs']
            for dvswitch in dvswitchs:
                portGroups = self.client.portgroups.list(dvswitch['urn'])['portGroups']
                for portGroup in portGroups:
                    portGroup['NetworkId'] = dvswitch['urn']
                resp.extend(portGroups)
        return patch_key(resp, constants.PORTGROUPS_MAPPER)

    @property
    def image(self):
        if self.resource_id:
            resp = [self.client.servers.get(self.resource_id)]
        else:
            resp = self.client.servers.list(self.site, params={'isTemplate': True})['vms']
        return patch_key(resp, constants.INSTANCE_MAPPER)

    @property
    def volume(self):
        if self.resource_id:
            resp = [self.client.volumes.get(self.resource_id)]
        else:
            resp = self.client.volumes.list(self.site)['volumes']
            if self.query_params.get('InstanceId'):
                resp = self.client.servers.get(self.query_params.get('InstanceId'))['vmConfig']['disks']
                return patch_key(resp, constants.VM_COMFIG_DISK_MAPPER)

        return patch_key(resp, constants.VOLUME_MAPPER)

    @property
    def volume_type(self):
        return [
            {
                "Id": "normal",
                "Name": "normal"
            },
            {
                "Id": "share",
                "Name": "share"
            },
        ]

    @staticmethod
    def portgroup2dvswitch(portgroup_urn):
        return ":".join(portgroup_urn.split(":")[:-2])
