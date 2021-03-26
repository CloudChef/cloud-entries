# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources import utils
from cloudchef_integration.tasks.cloud_resources.ucloud.constants import UCLOUD_REGION_NAME, UCLOUD_ZONE_NAME
from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import format_ins_status, format_power_status
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import FilterResponse


class UcloudStandardResponse(object):

    @classmethod
    def validate_empty(cls, resp, set_name='DataSet'):
        return resp.get(set_name, [])

    @classmethod
    def validation(cls, resp):
        regions = cls.validate_empty(resp, 'Regions')
        if not regions:
            raise Exception("Validation failed...Message:{}".format(resp.get('Message')))
        return regions

    @classmethod
    def region(cls, resp):
        regions = []
        ids = []
        for region in cls.validation(resp):
            if region['Region'] in list(UCLOUD_REGION_NAME.keys()):
                region['RegionName'] = UCLOUD_REGION_NAME[region['Region']]
            if region['Region'] not in ids:
                ids.append(region['Region'])
                regions.append({
                    "RegionId": region.get('RegionId'),
                    "Id": region.get('Region'),
                    "Name": region.get('RegionName'),
                    "Zone": region.get('Zone'),
                    "IsDefault": region.get('IsDefault')
                })
        return regions

    @classmethod
    def zone(cls, resp):
        zones = []
        for zone in cls.validation(resp):
            zones.append({
                "RegionId": zone.get('RegionId'),
                "RegionName": zone.get('RegionName'),
                "Id": zone.get('Zone'),
                "Name": UCLOUD_ZONE_NAME.get(zone.get('Zone')),
                "Region": zone.get('Region'),
                "IsDefault": zone.get('IsDefault')
            })
        return zones

    @classmethod
    def image(cls, resp):
        images = []
        resp = cls.validate_empty(resp, 'ImageSet')
        if not resp:
            return resp
        for image in resp:
            images.append({
                "Id": image.get("ImageId"),
                "Zone": image.get("Zone"),
                "ImageName": image.get("ImageName"),
                "ImageType": image.get("ImageType"),
                "ImageDescription": image.get("ImageDescription"),
                "MinimalCPU": image.get("MinimalCPU"),
                "Features": image.get("Features"),
                "PriceSet": image.get("PriceSet"),
                "CreateTime": image.get("CreateTime"),
                "Tag": image.get("Tag"),
                "ImageSize": image.get("ImageSize"),
                "OsType": image.get("OsType"),
                "Platform": image.get("OsType"),
                "State": image.get("State"),
                "Name": image.get("OsName")
            })
        return images

    @classmethod
    def instance(cls, resp):
        instances = []
        for ins in resp:
            instances.append({
                "Id": ins.get("UHostId"),
                "Zone": ins.get("Zone"),
                "LifeCycle": ins.get("LifeCycle"),
                "OsName": ins.get("OsName"),
                "ImageId": ins.get("ImageId"),
                "BasicImageId": ins.get("BasicImageId"),
                "BasicImageName": ins.get("BasicImageName"),
                "Tag": ins.get("Tag"),
                "Name": ins.get("Name"),
                "Remark": ins.get("Remark"),
                "State": format_ins_status(ins.get("State")),
                "NetworkState": ins.get("NetworkState"),
                "HostType": ins.get("HostType"),
                "StorageType": ins.get("StorageType"),
                "TotalDiskSpace": ins.get("TotalDiskSpace"),
                "DiskSet": ins.get("DiskSet"),
                "NetCapability": ins.get("NetCapability"),
                "IPSet": ins.get("IPSet"),
                "SubnetType": ins.get("SubnetType"),
                "IsolationGroup": ins.get("IsolationGroup"),
                "ChargeType": ins.get("ChargeType"),
                "ExpireTime": ins.get("ExpireTime"),
                "AutoRenew": ins.get("AutoRenew"),
                "IsExpire": ins.get("IsExpire"),
                "UHostType": ins.get("UHostType"),
                "OsType": ins.get("OsType"),
                "RdmaClusterId": ins.get("RdmaClusterId"),
                "CpuPlatform": ins.get("CpuPlatform"),
                "CreateTime": ins.get("CreateTime"),
                "CPU": ins.get("CPU"),
                "GPU": ins.get("GPU"),
                "Memory": ins.get("Memory"),
                "TimemachineFeature": ins.get("TimemachineFeature"),
                "HotplugFeature": ins.get("HotplugFeature"),
                "IPv6Feature": ins.get("IPv6Feature"),
                "EncryptedDiskFeature": ins.get("EncryptedDiskFeature"),
                "NetCapFeature": ins.get("NetCapFeature"),
                "MachineType": ins.get("MachineType"),
                "BootDiskState": ins.get("BootDiskState"),
                "CloudInitFeature": ins.get("CloudInitFeature"),
                "Status": format_ins_status(ins.get("State")),
                "PowerState": format_power_status(ins.get("State"))
            })
        return instances

    @classmethod
    def volume(cls, resp):
        volumes = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for volume in resp:
            volumes.append(
                {"ArkSwitchEnable": volume.get("ArkSwitchEnable"),
                 "BackupMode": volume.get("BackupMode"),
                 "ChargeType": volume.get("ChargeType"),
                 "CloneEnable": volume.get("CloneEnable"),
                 "CmkId": volume.get("CmkId"),
                 "CmkIdAlias": volume.get("CmkIdAlias"),
                 "CmkIdStatus": volume.get("CmkIdStatus"),
                 "CreateTime": volume.get("CreateTime"),
                 "DataKey": volume.get("DataKey"),
                 "DeviceName": volume.get("DeviceName"),
                 "DiskType": volume.get("DiskType"),
                 "ExpiredTime": volume.get("ExpiredTime"),
                 "Id": volume.get("UDiskId"),
                 "IsBoot": volume.get("IsBoot"),
                 "IsExpire": volume.get("IsExpire"),
                 "Name": volume.get("Name"),
                 "RdmaClusterId": volume.get("RdmaClusterId"),
                 "Size": volume.get("Size"),
                 "SnapEnable": volume.get("SnapEnable"),
                 "SnapshotCount": volume.get("SnapshotCount"),
                 "SnapshotLimit": volume.get("SnapshotLimit"),
                 "Status": volume.get("Status"),
                 "Tag": volume.get("Tag"),
                 "UDataArkMode": volume.get("UDataArkMode"),
                 "UDiskZoneId": volume.get("UDiskZoneId"),
                 "UHostIP": volume.get("UHostIP"),
                 "UHostId": volume.get("UHostId"),
                 "UHostName": volume.get("UHostName"),
                 "UKmsMode": volume.get("UKmsMode"),
                 "Version": volume.get("Version"),
                 "Zone": volume.get("Zone")}
            )
        return volumes

    @classmethod
    def volume_type(cls, resp):
        return [
            {'Id': 'DataDisk', 'Name': '普通数据盘'},
            {'Id': 'SSDDataDisk', 'Name': 'SSD数据盘'}]

    @classmethod
    def snapshot(cls, resp):
        snapshots = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for snap in resp:
            snapshots.append(
                {"ChargeType": snap.get("ChargeType"),
                 "Description": snap.get("Comment"),
                 "CreationDate": orchestra_utils.utctime_to_localtime(snap.get("CreateTime")),
                 "DiskType": snap.get("DiskType"),
                 "ExpiredTime": orchestra_utils.utctime_to_localtime(snap.get("ExpiredTime")),
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
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for net in resp:
            networks.append(
                {"CreateTime": net.get("CreateTime"),
                 "Name": net.get("Name"),
                 "Network": net.get("Network"),
                 "Cidr": net.get("NetworkInfo"),
                 "SubnetCount": net.get("SubnetCount"),
                 "Tag": net.get("Tag"),
                 "Id": net.get("VPCId"),
                 "Remark": net.get("Remark"),
                 "UpdateTime": net.get("UpdateTime"),
                 "OperatorName": net.get("OperatorName"),
                 "IPv6Network": net.get("IPv6Network"),
                 }
            )
        return networks

    @classmethod
    def subnet(cls, resp):
        subnets = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for subnet in resp:
            subnets.append(
                {"CreateTime": subnet.get("CreateTime"),
                 "Gateway": subnet.get("Gateway"),
                 "HasNATGW": subnet.get("HasNATGW"),
                 "Name": subnet.get("Name"),
                 "Netmask": subnet.get("Netmask"),
                 "Remark": subnet.get("Remark"),
                 "RouteTableId": subnet.get("RouteTableId"),
                 "Cidr": subnet.get("Subnet") + "/24",
                 "Id": subnet.get("SubnetId"),
                 "Type": subnet.get("SubnetType"),
                 "Tag": subnet.get("Tag"),
                 "NetworkId": subnet.get("VPCId"),
                 "VPCName": subnet.get("VPCName"),
                 "VRouterId": subnet.get("VRouterId"),
                 "Zone": subnet.get("Zone")}
            )
        return subnets

    @classmethod
    def security_group(cls, resp):
        securitygroups = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for sg in resp:
            securitygroups.append(
                {"CreateTime": sg.get("CreateTime"),
                 "Id": sg.get("FWId"),
                 "GroupId": sg.get("GroupId"),
                 "Name": sg.get("Name"),
                 "Remark": sg.get("Remark"),
                 "ResourceCount": sg.get("ResourceCount"),
                 "Rule": sg.get("Rule"),
                 "Tag": sg.get("Tag"),
                 "Type": sg.get("Type")}
            )
        return securitygroups

    @classmethod
    def eip(cls, resp):
        eips = []
        resp = cls.validate_empty(resp, 'EIPSet')
        if not resp:
            return resp
        for eip in resp:
            eips.append(
                {"Bandwidth": eip.get("Bandwidth"),
                 "BandwidthType": eip.get("BandwidthType"),
                 "ChargeType": eip.get("ChargeType"),
                 "CreateTime": eip.get("CreateTime"),
                 "EIPAddr": eip.get("EIPAddr"),
                 "Id": eip.get("EIPId"),
                 "Expire": eip.get("Expire"),
                 "ExpireTime": eip.get("ExpireTime"),
                 "Name": eip.get("Name"),
                 "PayMode": eip.get("PayMode"),
                 "Remark": eip.get("Remark"),
                 "Resource": eip.get("Resource"),
                 "ShareBandwidthSet": eip.get("ShareBandwidthSet"),
                 "Status": eip.get("Status"),
                 "Tag": eip.get("Tag"),
                 "Weight": eip.get("Weight")}
            )
        return eips


class UcloudFilterResponse(FilterResponse):

    @classmethod
    def filter_region(cls, params, regions):
        """
        filter one or multi region(s) according to region
        """
        if not params.get('region'):
            return regions
        aim = []
        for dct in regions:
            if dct['Region'] == params.get('region'):
                aim.append(dct)
        return aim
