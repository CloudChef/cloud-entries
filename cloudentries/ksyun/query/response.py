# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources import utils
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import format_ins_status
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import FilterResponse


class KsyunStandardResponse(object):

    @classmethod
    def validate_empty(cls, resp, set_name):
        return resp.get(set_name, [])

    @classmethod
    def validation(cls, resp, set_name='RegionSet'):
        regions = cls.validate_empty(resp, set_name)
        if not regions:
            raise Exception("Validation failed...Message:{}".format(resp.get('Message')))
        return regions

    @classmethod
    def region(cls, resp):
        regions = []
        for region in cls.validation(resp):
            regions.append({
                "Id": region.get('Region'),
                "Name": region.get('RegionName')
            })
        return regions

    @classmethod
    def zone(cls, resp):
        zones = []
        for zone in cls.validation(resp, 'AvailabilityZoneSet'):
            zones.append({
                "Id": zone.get('AvailabilityZone'),
                "Name": '可用区' + zone.get('AvailabilityZone')[-1].upper(),
                "Region": zone.get('Region')
            })
        return zones

    @classmethod
    def image(cls, resp):
        images = []
        resp = cls.validate_empty(resp, 'ImagesSet')
        if not resp:
            return resp
        for image in resp:
            if image.get("ImageState") == "active":
                images.append({
                    "Id": image.get("ImageId"),
                    "Name": image.get("Name"),
                    "ImageType": image.get("Platform"),
                    "CreateTime": image.get("CreationDate"),
                    "SysDisk": image.get("SysDisk"),
                    "OsType": image.get("Platform"),
                    "Platform": image.get("Platform"),
                    "ImageState": image.get("ImageState"),
                    "SnapshotSet": image.get("SnapshotSet")
                })
        return images

    @classmethod
    def instance(cls, resp):
        instances = []
        resp = cls.validate_empty(resp, 'InstancesSet')
        if not resp:
            return resp
        for ins in resp:
            data_disks = ins.get('DataDisks', [])
            system_disk = ins.get('SystemDisk', {}).get('DiskSize', 0)
            storage = sum([data_disk.get('DiskSize', 0) for data_disk in data_disks]) + system_disk
            networks = ins.get('NetworkInterfaceSet', {})
            public_ips = []
            private_ips = []
            network_id = ""
            for network in networks:
                if network.get('PrivateIpAddress'):
                    private_ips.append(network.get('PrivateIpAddress'))
                if network.get('PublicIp'):
                    public_ips.append(network.get('PublicIp'))
                if network.get('VpcId'):
                    network_id = network_id if network_id else network.get('VpcId')
            network_address = {
                "public_ip": ','.join(public_ips),
                "PrivateIpAddress": ','.join(private_ips)
            }

            instances.append({
                "Id": ins.get("InstanceId"),
                "Name": ins.get("InstanceName"),
                "InstanceType": ins.get("InstanceType"),
                "CPU": ins['InstanceConfigure'].get("VCPU"),
                "GPU": ins['InstanceConfigure'].get("GPU"),
                "Memory": ins['InstanceConfigure'].get("MemoryGb"),
                "Storage": storage,
                "ImageId": ins.get("ImageId"),
                "OperatingSystem": ins.get("ImageId"),
                "NetworkAddress": network_address,
                "PrivateIpAddress": ','.join(private_ips),
                "NetworkId": network_id,
                "Status": format_ins_status(ins['InstanceState']['Name'], default_status="uninitialized"),
                "SubnetId": ins.get("SubnetId"),
                "CreateTime": ins.get("CreationDate"),
                "Zone": ins.get("AvailabilityZone"),
                "ChargeType": ins.get("ChargeType"),
                "SystemDisk": ins.get("SystemDisk"),
                "DataDisks": ins.get("SystemDisk", []),
                "HostName": ins.get("HostName")
            })
        return instances

    @classmethod
    def local_volume(cls, resp):
        local_volumes = []
        resp = cls.validate_empty(resp, "LocalVolumeSet")
        if not resp:
            return resp
        for volume in resp:
            local_volumes.append(
                {
                    "Id": volume.get("LocalVolumeId"),
                    "Name": volume.get("LocalVolumeName"),
                    "Status": volume.get("LocalVolumeState"),
                    "InstanceId": volume.get("InstanceId"),
                    "InstanceName": volume.get("InstanceName"),
                    "InstanceState": volume.get("InstanceState"),
                    "DiskType": volume.get("LocalVolumeType"),
                    "Category": volume.get("LocalVolumeCategory"),
                    "Size": volume.get("LocalVolumeSize"),
                    "CreateTime": volume.get("CreationDate"),
                    "Local": True
                }
            )
        return local_volumes

    @classmethod
    def cloud_volume(cls, resp):
        cloud_volumes = []
        resp = cls.validate_empty(resp, "Volumes")
        if not resp:
            return resp
        for volume in resp:
            cloud_volumes.append(
                {
                    "Id": volume.get("VolumeId"),
                    "Name": volume.get("VolumeName"),
                    "Status": volume.get("VolumeStatus"),
                    "DiskType": volume.get("VolumeType"),
                    "Category": volume.get("VolumeCategory"),
                    "Size": volume.get("Size"),
                    "CreateTime": volume.get("CreateTime"),
                    "Local": False,
                    "Attachment": volume.get("Attachment", [])
                }
            )
        return cloud_volumes

    @classmethod
    def instance_volume(cls, resp):
        instance_volumes = []
        resp = cls.validate_empty(resp, "Attachments")
        if not resp:
            return resp
        for volume in resp:
            instance_volumes.append(
                {
                    "InstanceId": volume.get("InstanceId"),
                    "Id": volume.get("VolumeId"),
                    "Name": volume.get("VolumeName"),
                    "Status": volume.get('VolumeStatus'),
                    "Category": volume.get("VolumeCategory"),
                    "DiskType": volume.get("VolumeType"),
                    "Size": volume.get('Size'),
                    "CreateTime": volume.get("CreateTime"),
                    "Attachment": volume.get("Attachment", [])
                }
            )
        return instance_volumes

    @classmethod
    def local_volume_sp(cls, resp):
        local_volume_sps = []
        resp = cls.validate_empty(resp, "LocalVolumeSet")
        if not resp:
            return resp
        for snapshot in resp:
            local_volume_sps.append(
                {
                    "Id": snapshot.get("LocalVolumeSnapshotId"),
                    "Name": snapshot.get("LocalVolumeSnapshotName"),
                    "LocalVolumeState": snapshot.get("LocalVolumeState"),
                    "Description": snapshot.get("LocalVolumeSnapshotDesc"),
                    "VolumeId": snapshot.get("SourceLocalVolumeId"),
                    "VolumeName": snapshot.get("SourceLocalVolumeName"),
                    "VolumeCategory": snapshot.get("SourceLocalVolumeCategory"),
                    "VolumeStatus": snapshot.get("SourceLocalVolumeState"),
                    "Status": snapshot.get("State"),
                    "CreateTime": snapshot.get("CreationDate"),
                    "InstanceId": snapshot.get("InstanceId"),
                    "Size": snapshot.get("DiskSize"),
                    "SnapshotType": snapshot.get("SnapshotType")
                }
            )
        return local_volume_sps

    @classmethod
    def snapshot(cls, resp):
        snapshots = []
        resp = cls.validate_empty(resp, "Snapshots")
        if not resp:
            return resp
        for snap in resp:
            snapshots.append(
                {"ChargeType": snap.get("ChargeType"),
                 "Description": snap.get("Comment"),
                 "CreationDate": utils.utctime_to_localtime(snap.get("CreateTime")),
                 "DiskType": snap.get("DiskType"),
                 "ExpiredTime": utils.utctime_to_localtime(snap.get("ExpiredTime")),
                 "VolumeStatus": snap.get("IsUDiskAvailable"),
                 "Name": snap.get("Name"),
                 "Size": snap.get("Size"),
                 "Id": snap.get("SnapshotId"),
                 "Status": snap.get("Status"),
                 "VolumeId": snap.get("UDiskId"),
                 "VolumeName": snap.get("UDiskName"),
                 "UHostId": snap.get("UHostId"),
                 "Version": snap.get("Version")}
            )
        return snapshots

    @classmethod
    def network(cls, resp):
        networks = []
        resp = cls.validate_empty(resp, "VpcSet")
        if not resp:
            return resp
        for vpc in resp:
            networks.append(
                {
                    "Id": vpc.get("VpcId"),
                    "Name": vpc.get("VpcName"),
                    "Cidr": vpc.get("CidrBlock"),
                    "CreateTime": vpc.get("CreateTime")
                }
            )
        return networks

    @classmethod
    def subnet(cls, resp):
        subnets = []
        resp = cls.validate_empty(resp, "SubnetSet")
        if not resp:
            return resp
        for subnet in resp:
            if subnet.get("SubnetType") in ["Normal", "Reserve", "Physical"]:
                subnets.append(
                    {"Id": subnet.get("SubnetId"),
                     "Name": subnet.get("SubnetName"),
                     "NetworkId": subnet.get("VpcId"),
                     "Cidr": subnet.get("CidrBlock"),
                     "SubnetType": subnet.get("SubnetType"),
                     "CreateTime": subnet.get("CreateTime"),
                     "Dns1": subnet.get("Dns1"),
                     "Dns2": subnet.get("Dns2"),
                     "GatewayIp": subnet.get("GatewayIp"),
                     "Zone": subnet.get("AvailabilityZoneName")
                     }
                )
        return subnets

    @classmethod
    def security_group(cls, resp):
        securitygroups = []
        resp = cls.validate_empty(resp, "SecurityGroupSet")
        if not resp:
            return resp
        for sg in resp:
            securitygroups.append(
                {
                    "Id": sg.get("SecurityGroupId"),
                    "Name": sg.get("SecurityGroupName"),
                    "CreateTime": sg.get("CreateTime"),
                    "VpcId": sg.get("VpcId"),
                    "Rule": sg.get("SecurityGroupEntrySet"),
                    "Type": sg.get("SecurityGroupType")}
            )
        return securitygroups

    @classmethod
    def eip(cls, resp):
        eips = []
        resp = cls.validate_empty(resp, 'AddressesSet')
        if not resp:
            return resp
        for eip in resp:
            eips.append(
                {
                    "CreateTime": eip.get("CreateTime"),
                    "PublicIp": eip.get("PublicIp"),
                    "Id": eip.get("AllocationId"),
                    "LineId": eip.get("LineId"),
                    "BandWidth": eip.get("BandWidth"),
                    "State": eip.get("State"),
                    "InstanceType": eip.get("InstanceType"),
                    "InstanceId": eip.get("InstanceId")}
            )
        return eips

    @classmethod
    def flavor(cls, resp):
        flavors = []
        resp = cls.validate_empty(resp, 'InstanceTypeConfigSet')
        if not resp:
            return resp
        for flavor in resp:
            flavor_name = 'InstanceFamily:{} CPU:{} Memory:{}'.format(flavor.get("InstanceFamily"), flavor.get("CPU"),
                                                                      flavor.get("Memory"))
            flavors.append(
                {
                    "Id": flavor.get("InstanceType"),
                    "Name": flavor_name,
                    "InstanceFamily": flavor.get("InstanceFamily"),
                    "InstanceFamilyName": flavor.get("InstanceFamily"),
                    "CPU": flavor.get("CPU"),
                    "Memory": flavor.get("Memory"),
                    "SystemDiskQuotaSet": flavor.get("SystemDiskQuotaSet"),
                    "DataDiskQuotaSet": flavor.get("DataDiskQuotaSet"),
                    "AvailabilityZoneSet": flavor.get("AvailabilityZoneSet")
                }
            )
        return flavors

    @classmethod
    def family(cls, resp):
        families = []
        resp = cls.validate_empty(resp, 'InstanceFamilySet')
        if not resp:
            return resp
        for family in resp:
            families.append(
                {
                    "Id": family.get("InstanceFamily"),
                    "Name": family.get("InstanceFamilyName"),
                    "AvailabilityZoneSet": family.get("AvailabilityZoneSet")
                }
            )
        return families

    @classmethod
    def line(cls, resp):
        lines = []
        resp = cls.validate_empty(resp, 'LineSet')
        if not resp:
            return resp
        for line in resp:
            if line.get("LineName") == "BGP":
                lines.append(
                    {
                        "Id": line.get("LineId"),
                        "Name": line.get("LineName"),
                        "IpVersion": line.get("IpVersion"),
                        "LineType": line.get("LineType"),
                    }
                )
        return lines

    @classmethod
    def lblistener(cls, resp):
        listeners = []
        resp = cls.validate_empty(resp, 'ListenerSet')
        if not resp:
            return resp
        for listener in resp:
            listeners.append({
                "Id": listener["LoadBalancerId"],
                "Name": listener["ListenerName"],
                "Protocol": listener["ListenerProtocol"],
                "Port": listener["ListenerPort"],
                "Method": listener["Method"],
                "SessionState": format_ins_status(listener["Session"]["SessionState"]),
                "BackendNum": len(listener["RealServer"]),
                "RealServer": [{"Ip": server["RealServerIp"], "Port": server["RealServerPort"],
                                "Weight": server["Weight"]} for server in listener["RealServer"]]
            })
        return listeners


class KsyunFilterResponse(FilterResponse):

    @classmethod
    def filter_eip_state(cls, params, resp):
        """
        filter one or multi region(s) according to region
        """
        if not params.get('State'):
            return resp
        aim = []
        for dct in resp:
            if dct['State'] == params.get('State'):
                aim.append(dct)
        return aim

    @classmethod
    def filter_volume_type(cls, params, resp):
        """
        filter one or multi region(s) according to region
        """
        category = params.get('category', "")
        aim = []
        if category == "systemDisk":
            if not resp:
                return aim
            system_disk_set = resp[0]["SystemDiskQuotaSet"]
            for system_disk in system_disk_set:
                aim.append({
                    "Id": system_disk.get("SystemDiskType"),
                    "Name": system_disk.get("SystemDiskType")
                })
        elif category == "dataDisk":
            if not resp:
                return aim
            data_disk_set = resp[0]["DataDiskQuotaSet"]
            for data_disk in data_disk_set:
                aim.append({
                    "Id": data_disk.get("DataDiskType"),
                    "Name": data_disk.get("DataDiskType")
                })
        else:
            aim = [{'Id': 'SSD3.0', 'Name': 'SSD3.0'},
                   {'Id': 'EHDD', 'Name': 'EHDD'},
                   {'Id': "Local_SSD", "Name": "Local_SSD"}]
        return aim
