# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from .connection import Conn_GCP
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import patch_key, format_ins_status, filter_flavor
from cloudchef_integration.tasks.cloud_resources.gcp import constants


class GCPClient(object):
    def __init__(self, connection_config, query_params=None):
        self.private_key_id = connection_config.get('private_key_id')
        self.private_key = connection_config.get('private_key')
        self.client_email = connection_config.get('client_email')
        self.client_id = connection_config.get('client_id')
        self.project_id = connection_config.get('project_id')
        self.site = connection_config.get('region', None)
        self.query_params = query_params
        self.resource_id = query_params.get('resource_id')
        self.client = Conn_GCP(
            private_key_id=self.private_key_id,
            private_key=self.private_key.replace('\\n', '\n'),
            client_email=self.client_email,
            client_id=self.client_id
        ).get_service()

    @property
    def validation(self):
        return self.region

    @property
    def region(self):
        if self.resource_id:
            resp = [self.client.regions().get(project=self.project_id, region=self.resource_id).execute()]
        else:
            resp = self.client.regions().list(project=self.project_id).execute()['items']
        return patch_key(self.modify_value(resp), constants.REGION_MAPPER)

    @property
    def zone(self):
        zones = self.get_zones_from_region(self.client, self.project_id, self.site)
        resp = []
        if self.resource_id:
            resource_config = self.client.zones().get(project=self.project_id, zone=self.resource_id).execute()
            resp.append(resource_config)
        else:
            for zone in zones:
                response = self.client.zones().get(project=self.project_id, zone=zone).execute()
                resp.append(response)
        for obj in resp:
            obj['region'] = obj['region'].split('/')[-1]
        return patch_key(self.modify_value(resp), constants.ZONE_MAPPER)

    @property
    def network(self):
        if self.resource_id:
            resp = [self.client.networks().get(project=self.project_id, network=self.resource_id).execute()]
        else:
            resp = self.client.networks().list(project=self.project_id).execute()['items']
        return patch_key(self.modify_value(resp), constants.NETWORK_MAPPER)

    @property
    def subnet(self):
        resp = []
        if self.resource_id:
            resource_config = self.client.subnetworks().get(project=self.project_id, region=self.site,
                                                            subnetwork=self.resource_id).execute()
            resp.append(resource_config)
        if self.query_params.get('NetworkId'):
            network_id = self.query_params.get('NetworkId')
            subnetworks = self.get_subnetworks_from_network(self.client, self.project_id, network_id)
            for subnetwork in subnetworks:
                subnetwork_config = self.client.subnetworks().get(project=self.project_id, region=self.site,
                                                                  subnetwork=subnetwork).execute()
                resp.append(subnetwork_config)
        else:
            resp = self.client.subnetworks().list(project=self.project_id, region=self.site).execute()['items']
        for port_group in resp:
            port_group['network'] = port_group['network'].split('/')[-1]
            port_group['region'] = port_group['region'].split('/')[-1]
        return patch_key(self.modify_value(resp), constants.PORTGROUPS_MAPPER)

    @property
    def flavor(self):
        zones = self.get_zones_from_region(self.client, self.project_id, self.site)
        resp = []
        if self.resource_id:
            for zone in zones:
                try:
                    resource_config = self.client.machineTypes().get(project=self.project_id, zone=zone,
                                                                     machineType=self.resource_id)
                    response = resource_config.execute()
                    resp.append(response)
                except Exception as e:
                    pass
        else:
            for zone in zones:
                try:
                    response = self.client.machineTypes().list(project=self.project_id, zone=zone).execute()['items']
                    resp += response
                except Exception as e:
                    pass
        resp = patch_key(self.add_machine_type(resp), constants.FLAVOR_MAPPER)
        return filter_flavor(resp, self.query_params, by_name=True)

    @property
    def image(self):
        if self.resource_id:
            resource = self.resource_id.split('/')
            resp = [self.client.images().getFromFamily(project=resource[0], family=resource[1]).execute()]
        else:
            resp = []
            for project, familys in list(constants.GCP_PUBLIC_PROJECT.items()):
                for family in familys:
                    dic = {}
                    dic['id'] = project + '/' + family
                    dic['name'] = family
                    resp.append(dic)
        return patch_key(resp, constants.INSTANCE_MAPPER)

    @property
    def volume(self):
        zones = self.get_zones_from_region(self.client, self.project_id, self.site)
        resp = []
        if self.resource_id:
            for zone in zones:
                try:
                    resource_config = self.client.disks().get(project=self.project_id, zone=zone, disk=self.resource_id)
                    response = resource_config.execute()
                    resp.append(response)
                except Exception as e:
                    pass
        else:
            for zone in zones:
                try:
                    response = self.client.disks().list(project=self.project_id, zone=zone).execute()['items']
                    resp += response
                except Exception:
                    pass
            if self.query_params.get('InstanceId'):
                for zone in zones:
                    try:
                        resp = self.client.instances().get(project=self.project_id, zone=zone,
                                                           instance=self.query_params.get('InstanceId')).execute()[
                            'disks']
                        for obj in resp:
                            obj['id'] = obj['deviceName']
                        return patch_key(resp, constants.VM_DISK_MAPPER)
                    except Exception as e:
                        pass
        return patch_key(resp, constants.VOLUME_MAPPER)

    @property
    def volume_type(self):
        zones = self.get_zones_from_region(self.client, self.project_id, self.site)
        resp = []
        temporary_storage = []
        if self.resource_id:
            for zone in zones:
                try:
                    resource_config = self.client.diskTypes().get(project=self.project_id, zone=zone,
                                                                  diskType=self.resource_id).execute()
                    temporary_storage.append(resource_config)
                except Exception as e:
                    pass
        else:
            for zone in zones:
                try:
                    resource_config = self.client.diskTypes().list(project=self.project_id, zone=zone).execute()[
                        'items']
                    temporary_storage += resource_config
                except Exception:
                    pass
        for obj in temporary_storage:
            if obj['name'] != 'local-ssd':
                obj['id'] = obj['name']
                resp.append(obj)
        return patch_key(resp, constants.VOLUME_TYPE_MAPPER)

    @property
    def instance(self):
        zones = self.get_zones_from_region(self.client, self.project_id, self.site)
        resp = []
        if self.resource_id:
            for zone in zones:
                try:
                    resource_info = self.client.instances().get(project=self.project_id, zone=zone,
                                                                instance=self.resource_id).execute()
                    resource_info["status"] = format_ins_status(resource_info["status"])
                    resp.append(resource_info)
                except Exception as e:
                    pass
        else:
            for zone in zones:
                try:
                    response = self.client.instances().list(project=self.project_id, zone=zone).execute()['items']
                    for instance in response:
                        instance["status"] = format_ins_status(instance["status"])
                        resp.append(instance)
                except Exception:
                    pass
        return patch_key(self.modify_value(resp), constants.INSTANCE_MAPPER)

    @property
    def security_group(self):
        if self.resource_id:
            resp = [self.client.firewalls().get(project=self.project_id, firewall=self.resource_id).execute()]
        else:
            resp = self.client.firewalls().list(project=self.project_id).execute()['items']
        return patch_key(self.modify_value(resp), constants.SECURITY_GROUP_MAPPER)

    @staticmethod
    def get_zones_from_region(client, project_id, region):
        zones = []
        zones_link = client.regions().get(project=project_id, region=region).execute()['zones']
        for zone in zones_link:
            zones.append(zone.split('/')[-1])
        return zones

    @staticmethod
    def get_subnetworks_from_network(client, project_id, network):
        subnetworks = []
        subnetworks_link = client.networks().get(project=project_id, network=network).execute()['subnetworks']
        for subnetwork in subnetworks_link:
            subnetworks.append(subnetwork.split('/')[-1])
        return subnetworks

    @staticmethod
    def modify_value(resp):
        for obj in resp:
            obj['id'] = obj['name']
        return resp

    @staticmethod
    def add_machine_type(resp):
        for obj in resp:
            obj['id'] = obj['name']
            spec_type = obj.get('name').split('-')[0]
            if spec_type == 'c2':
                obj['name'] = obj.get('name') + '/' + obj.get('description').split(':')[1]
            elif spec_type == 'e2':
                obj['name'] = obj.get('name') + '/' + obj.get('description').split(',', 1)[1]
            else:
                obj['name'] = obj.get('name') + '/' + obj.get('description')

        return resp
