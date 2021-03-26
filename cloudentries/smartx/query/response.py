# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import format_ins_status, format_power_status
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import FilterResponse


class SmartXStandardResponse(object):

    @classmethod
    def image(cls, resp):
        images = []
        for image in resp:
            images.append({
                "Id": image.get("uuid"),
                "Name": image.get("name"),
                "Cpu": image.get("cpu"),
                "Vcpu": image.get("vcpu"),
                "Memory": image.get("memory") >> 30,
                "CreateTime": image.get("create_time"),
                "Description": image.get("description"),
                "Disks": image.get("disks"),
                "Nics": image.get("nics"),
                "Status": image.get("status"),
                "Type": image.get("type")
            })
        return images

    @classmethod
    def storage_policy(cls, resp):
        policies = []
        for policy in resp:
            policies.append({
                "Id": policy.get("uuid"),
                "CreatedTime": policy.get("created_time"),
                "Datastores": policy.get("datastores"),
                "Description": policy.get("description"),
                "Name": policy.get("name"),
                "ReadOnly": policy.get("read_only"),
                "ResourceState": policy.get("resource_state"),
                "StoragePoolId": policy.get("storage_pool_id")
            })
        return policies

    @classmethod
    def instance(cls, resp):
        instances = []
        for ins in resp:
            operating_system = ins['guest_info'].get('os_version', '')
            if operating_system:
                operating_system = operating_system.lower()
            ip_address_list = []
            for nic in ins['nics']:
                ip_address_list.append(nic.get('ip_address') or nic.get('mac_address'))
            instances.append({
                "Id": ins.get("uuid"),
                "Name": ins.get("vm_name"),
                "CPU": ins.get("vcpu"),
                "CpuModel": ins.get("cpu_model"),
                "CreateTime": ins.get("create_time"),
                "Description": ins.get("description"),
                "Disks": ins.get("disks"),
                "GuestInfo": ins.get("guest_info"),
                "Memory": ins.get("memory") >> 30,
                "Nics": ins.get("nics"),
                "OperatingSystem": operating_system,
                "Powerstate": format_power_status(ins['status']),
                "NetworkAddress": ",".join(ip_address_list),
                "Status": format_ins_status(ins['status']),
                "NodeIp": ins.get("node_ip"),
                "Vcpu": ins.get("vcpu"),
                "Cpu": ins.get("vcpu") or ins['cpu']['topology']['cores'],
            })
        return instances

    @classmethod
    def volume(cls, resp):
        volumes = []
        for volume in resp:
            category = "system" if volume.get("name") == "1" else "data"
            volumes.append(
                {
                    "Id": volume.get("uuid"),
                    "Name": volume.get("name"),
                    "Size": volume.get("size_in_byte") >> 30,
                    "Status": volume.get("status"),
                    "Description": volume.get("description"),
                    "ResourceState": volume.get("resource_state"),
                    "DiskType": 'CLOUD_PREMIUM',
                    "Category": category
                }
            )
        return volumes

    @classmethod
    def vm_volume(cls, resp):
        volumes = []
        for volume in resp:
            category = "system" if volume.get("name") == "1" else "data"
            if volume.get("volume_uuid"):
                size_in_byte = volume.get("size_in_byte") or volume.get("size")
                volumes.append(
                    {
                        "Id": volume.get("volume_uuid"),
                        "Name": volume.get("name"),
                        "Size": size_in_byte >> 30,
                        "DiskType": 'CLOUD_PREMIUM',
                        "Category": category,
                        "Status": "created"
                    }
                )
        return volumes

    @classmethod
    def network(cls, resp):
        networks = []
        for net in resp:
            networks.append(
                {
                    "Id": net.get("uuid"),
                    "Name": net.get("name"),
                    "BondMode": net.get("bond_mode"),
                    "BondName": net.get("bond_name"),
                    "Description": net.get("description"),
                    "HostsAssociated": net.get("hosts_associated"),
                    "HostsInitialized": net.get("hosts_initialized"),
                    "VlansCount": net.get("vlans_count"),
                    "Usage": net.get("usage"),
                    "Type": net.get("type")
                }
            )
        return networks

    @classmethod
    def subnet(cls, resp):
        subnets = []
        for subnet in resp:
            subnets.append(
                {
                    "Id": subnet.get("uuid"),
                    "Name": subnet.get("name"),
                    "Type": subnet.get("type"),
                    "VlanId": subnet.get("vlan_id"),
                    "NetworkId": subnet.get("vds_uuid")
                }
            )
        return subnets


class SmartXFilterResponse(FilterResponse):

    @classmethod
    def filter_volume_type(cls, params, resp):
        """
        filter one or multi region(s) according to region
        """
        volume_category = params.get('volume_category', "")
        if not volume_category or volume_category != "data":
            return resp
        aim = []
        for dct in resp:
            if dct.get("Category") == "data":
                aim.append(dct)
        return aim
