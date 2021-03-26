from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import format_power_status, format_ins_status
from cloudchef_integration.tasks.cloud_resources.commoncloud.response import FilterResponse


class ZstackStandardResponse:
    @classmethod
    def instance(cls, resp):
        instances = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for ins in resp:
            if ins.get("state") == 'Destroyed':
                continue
            vm_nics = ins.get("vmNics", [])
            private_ip = [nic.get("ip", "") for nic in vm_nics]
            network_address = {
                'private_ip': ",".join(private_ip)
            }
            instances.append({
                "Id": ins.get("uuid"),
                "Name": ins.get("name"),
                "Status": format_ins_status(ins.get("state")),
                "PowerState": format_power_status(ins.get("state")),
                "description": ins.get("description"),
                "ImageId": ins.get("imageUuid"),
                "hostId": ins.get("hostUuid"),
                "platform": ins.get("platform"),
                "Memory": int(ins.get("memorySize") >> 30),
                "CPU": int(ins.get("cpuNum")),
                "CreateTime": ins.get("createDate"),
                "PrivateIpAddresses": private_ip,
                "NetworkAddress": network_address
            })
        return instances

    @classmethod
    def image(cls, resp):
        images = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for image in resp:
            images.append({
                "Id": image.get("uuid"),
                "Name": image.get("name"),
                "State": image.get("state"),
                "ImageDescription": image.get("description"),
                "CreateTime": image.get("createDate"),
                "Platform": image.get("platform"),
                "OsType": image.get("platform"),
                "ImageType": image.get("platform"),
                "ImageSize": image.get("size") >> 30
            })

        return images

    @classmethod
    def flavor(cls, resp):
        flavors = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for flavor in resp:
            flavors.append({
                "Id": flavor.get("uuid"),
                "Name": flavor.get("name"),
                "Status": flavor.get("state"),
                "CPU": int(flavor.get("cpuNum")),
                "Memory": flavor.get("memorySize") >> 30,
                "type": flavor.get("type")
            })
        return flavors

    @classmethod
    def validate_empty(cls, resp, set_name='inventories'):
        return resp.get(set_name, [])

    @classmethod
    def volume(cls, resp):
        volumes = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for volume in resp:
            volumes.append({
                "Id": volume.get("uuid"),
                "Name": volume.get("name"),
                "HostId": volume.get("vmInstanceUuid"),
                "ImageId": volume.get("rootImageUuid"),
                "Category": "system" if volume.get('type') == 'Root' else 'data',
                "DiskType": "CLOUD_PREMIUM",
                "Size": int(volume.get("size") >> 30),
                "status": volume.get("status"),
                "Status": volume.get("state"),
                "CreateTime": volume.get("createDate")
            })
        return volumes

    @classmethod
    def snapshot(cls, resp):
        snapshots = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for snapshot in resp:
            snapshots.append({
                "Id": snapshot.get("uuid"),
                "Name": snapshot.get("name"),
                "DiskType": snapshot.get("volumeType"),
                "Size": snapshot.get("size") >> 20,
                "VolumeId": snapshot.get("volumeUuid"),
                "status": snapshot.get("status"),
                "Description": snapshot.get("description"),
                "Status": snapshot.get("state")
            })
        return snapshots

    @classmethod
    def vlan(cls, resp):
        vlans = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for vlan in resp:
            vlans.append({
                "Id": str(vlan.get("uuid")),
                "Name": vlan.get("name"),
                "description": vlan.get("description"),
                "Vlan": vlan.get("vlan"),
                "Type": vlan.get("type")
            })
        return vlans

    @classmethod
    def vxlan(cls, resp):
        vxlans = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for vxlan in resp:
            vxlans.append({
                "Name": vxlan.get("name"),
                "description": vxlan.get("description"),
                "Type": vxlan.get("type")
            })
        return vxlans

    @classmethod
    def volume_type(cls, resp):
        volume_types = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for volume_type in resp:
            volume_types.append({
                "Id": volume_type.get("uuid"),
                "Name": volume_type.get("name"),
                "Size": volume_type.get("diskSize") >> 30
            })
        return volume_types

    @classmethod
    def securitygroup(cls, resp):
        security_groups = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for security_group in resp:
            security_groups.append({
                "Id": security_group.get("uuid"),
                "Name": security_group.get("name"),
                "SecurityGroupDesc": security_group.get("description"),
                "Status": security_group.get("state"),
                "CreateTime": security_group.get("createDate"),
                "Rule": security_group.get("rules"),
                "attachedL3NetworkUuids": security_group.get("attachedL3NetworkUuids")
            })
        return security_groups

    @classmethod
    def vpc(cls, resp):
        vpcs = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for vpc in resp:
            vpcs.append({
                "Id": vpc.get("uuid"),
                "Name": vpc.get("name"),
                "dns": vpc.get("dns"),
                "description": vpc.get("description"),
                "Type": vpc.get("platform"),
                "vmNics": vpc.get("vmNics"),
                "Status": vpc.get("state")
            })
        return vpcs

    @classmethod
    def subnet(cls, resp):
        subnets = []
        resp = cls.validate_empty(resp)
        if not resp:
            return resp
        for subnet in resp:
            ipranges = subnet.get("ipRanges", [])
            cidr = ipranges[0].get('networkCidr') if ipranges else ""
            subnets.append({
                "Id": subnet.get("uuid"),
                "Name": subnet.get("name"),
                "Type": subnet.get("type"),
                "Status": subnet.get("state"),
                "Network": subnet.get("networkServices"),
                "NetworkId": subnet.get("l2NetworkUuid"),
                "ipVersion": subnet.get("ipVersion"),
                "category": subnet.get("category"),
                "CreateTime": subnet.get("createDate"),
                "dns": subnet.get("dns"),
                "hostRoute": subnet.get("hostRoute"),
                "ipRanges": ipranges,
                "Cidr": cidr
            })
        return subnets


class ZstackFilterResponse(FilterResponse):

    @classmethod
    def filter_instance(cls, params, resp):
        """
        filter volumes according to InstanceId
        """
        if not params.get('InstanceId'):
            return resp
        aim = []
        instance_ids = params.get('InstanceId').split(',')
        for dct in resp:
            if dct['HostId'] in instance_ids:
                aim.append(dct)
        return aim

    @classmethod
    def filter_volume_type(cls, params, resp):
        """
        filter volumes accoring to volume_category
        """
        if not resp:
            return resp
        category = params.get('category', "")
        aim = []
        if category == "systemDisk":
            for volume in resp:
                if volume.get("DiskType") == "Root":
                    aim.append(volume)
        elif category == "dataDisk":
            for volume in resp:
                if volume.get("DiskType") == "Data":
                    aim.append(volume)
        else:
            return resp
        return aim
