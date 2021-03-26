# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import format_ins_status, format_power_status


class TencentStandardResponse(object):

    @classmethod
    def region(cls, resp):
        regions = []
        for region in resp:
            if region.RegionState == 'AVAILABLE':
                regions.append({
                    "Id": region.Region,
                    "Name": region.RegionName
                })
        return regions

    @classmethod
    def zone(cls, resp):
        zones = []
        for zone in resp:
            if zone.ZoneState == 'AVAILABLE':
                zones.append({
                    "Id": zone.Zone,
                    "Name": zone.ZoneName,
                    "Zone": zone.Zone
                })

        return zones

    @classmethod
    def image(cls, resp):
        images = []
        for image in resp:
            images.append({
                "Id": image.ImageId,
                "ImageName": image.OsName,
                "ImageType": image.ImageType,
                "ImageDescription": image.ImageDescription,
                "CreateTime": image.CreatedTime,
                "ImageSize": image.ImageSize,
                "OsType": image.Platform,
                "Platform": image.Platform,
                "State": image.ImageState,
                "Name": image.OsName
            })
        return images

    @classmethod
    def instance(cls, resp):
        instances = []
        for ins in resp:
            storage_size = 0
            if ins.SystemDisk and ins.SystemDisk.DiskSize:
                storage_size += ins.SystemDisk.DiskSize
            if ins.DataDisks and ins.DataDisks:
                for data_disk in ins.DataDisks:
                    storage_size += data_disk.DiskSize
            public_ip = ','.join(ins.PublicIpAddresses) if ins.PublicIpAddresses else ''
            private_ip = ','.join(ins.PrivateIpAddresses) if ins.PrivateIpAddresses else ''
            network_address = {
                'public_ip': public_ip,
                'private_ip': private_ip
            }
            instances.append({
                "Id": ins.InstanceId,
                "Uuid": ins.Uuid,
                "Name": ins.InstanceName,
                "Zone": ins.Placement.Zone,
                "OperatingSystem": ins.OsName.lower(),
                "ImageId": ins.ImageId,
                "Storage": storage_size,
                "NetworkAddress": network_address,
                "Status": format_ins_status(ins.InstanceState),
                "CreateTime": ins.CreatedTime,
                "ExpireTime": ins.ExpiredTime,
                "Memory": ins.Memory,
                "CPU": ins.CPU,
                "ChargeType": ins.InstanceChargeType,
                "SystemDisk": json.loads(ins.SystemDisk.to_json_string()),
                "Placement": json.loads(ins.Placement.to_json_string()),
                "PrivateIpAddresses": ins.PrivateIpAddresses,
                "PublicIpAddresses": ins.PublicIpAddresses,
                "DataDisks": ins.DataDisks,
                "VirtualPrivateCloud": json.loads(ins.VirtualPrivateCloud.to_json_string()),
                "PowerState": format_power_status(ins.InstanceState),
                "InstanceType": ins.InstanceType,
                "SecurityGroupIds": ins.SecurityGroupIds,
                "Tags": [{"Key": tag.Key, "Value": tag.Value} for tag in ins.Tags]
            })
        return instances

    @classmethod
    def volume(cls, resp):
        volumes = []
        for volume in resp:
            volumes.append(
                {
                    "Id": volume.DiskId,
                    "Name": volume.DiskName,
                    "Size": volume.DiskSize,
                    "Status": volume.DiskState,
                    "DiskType": volume.DiskType,
                    "InstanceId": volume.InstanceId,
                    "Category": 'system' if volume.DiskUsage == 'SYSTEM_DISK' else 'data',
                    "CreateTime": volume.CreateTime,
                    "DiskSize": volume.DiskSize,
                    "Attached": volume.Attached,
                    "DiskChargeType": volume.DiskChargeType
                }
            )
        return volumes

    @classmethod
    def volume_type(cls, resp):
        volumes_type = []
        for volume_type in resp:
            volumes_type.append(
                {
                    "Id": volume_type.DiskType,
                    "Name": volume_type.DiskType
                }
            )
        return volumes_type

    @classmethod
    def snapshot(cls, resp):
        snapshots = []
        for snap in resp:
            snapshots.append(
                {
                    "CreationDate": snap.CreateTime,
                    "DiskType": snap.DiskType,
                    "ExpiredTime": snap.DeadlineTime,
                    "VolumeStatus": snap.SnapshotState,
                    "Name": snap.SnapshotName,
                    "Size": snap.DiskSize,
                    "Id": snap.SnapshotId,
                    "Status": snap.Status,
                    "VolumeId": snap.DiskId
                }
            )
        return snapshots

    @classmethod
    def network(cls, resp):
        networks = []
        for net in resp:
            networks.append(
                {"CreateTime": net.CreatedTime,
                 "Name": net.VpcName,
                 "Cidr": net.CidrBlock,
                 "Tag": net.TagSet,
                 "Id": net.VpcId,
                 "DnsServerSet": net.DnsServerSet,
                 "IPv6Network": net.Ipv6CidrBlock,
                 }
            )
        return networks

    @classmethod
    def subnet(cls, resp):
        subnets = []
        for subnet in resp:
            subnets.append(
                {
                    "Id": subnet.SubnetId,
                    "Name": subnet.SubnetName,
                    "CreateTime": subnet.CreatedTime,
                    "Cidr": subnet.CidrBlock,
                    "Zone": subnet.Zone,
                    "NetworkId": subnet.VpcId
                }
            )
        return subnets

    @classmethod
    def security_group(cls, resp):
        securitygroups = []
        for sg in resp:
            securitygroups.append(
                {
                    "Id": sg.SecurityGroupId,
                    "Name": sg.SecurityGroupName,
                    "SecurityGroupDesc": sg.SecurityGroupDesc,
                }
            )
        return securitygroups

    @classmethod
    def flavor(cls, resp):
        flavors = []
        for flavor in resp:
            flavor_name = 'InstanceFamily:{} CPU:{} Memory:{}'.format(flavor.InstanceFamily, flavor.CPU, flavor.Memory)
            flavors.append(
                {
                    "Id": flavor.InstanceType,
                    "Name": flavor_name,
                    "Zone": flavor.Zone,
                    "InstanceFamily": flavor.InstanceFamily,
                    "GPU": flavor.GPU,
                    "CPU": flavor.CPU,
                    "Memory": flavor.Memory
                }
            )
        return flavors

    @classmethod
    def balance(cls, resp):
        balance = {}
        balance['Balance'] = resp.Balance
        return [balance]
