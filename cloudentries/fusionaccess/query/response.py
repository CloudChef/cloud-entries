# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

class FusionAccessStandardResponse(object):

    @classmethod
    def validate_empty(cls, resp, set_name='DataSet'):
        return resp.get(set_name, [])

    @classmethod
    def validation(cls, resp):
        if not resp:
            raise Exception("Validation failed...Message:{}".format(resp))
        return [{"Id": resp}]

    @classmethod
    def site(cls, resp):
        sites = []
        for site in cls.validate_empty(resp, set_name='sites'):
            sites.append({
                "Id": site.get("siteId"),
                "Name": site.get("name"),
            })
        return sites

    @classmethod
    def cluster(cls, resp):
        clusters = []
        for cluster in cls.validate_empty(resp, set_name='clusters'):
            clusters.append({
                "Id": cluster.get("clusterId"),
                "Name": cluster.get("name"),
            })
        return clusters

    @classmethod
    def instance(cls, resp):
        instances = []
        for instance in cls.validate_empty(resp, set_name='instancesInfoList'):
            os_platform = instance.get("osPlatform")
            os_type = "windows" if os_platform == 0 else "linux"
            instances.append({
                "Id": instance.get("vmId"),
                "Name": instance.get("computerName"),
                "Status": instance.get("instanceState"),
                "OsType": os_type,
                "OperatingSystem": os_type,
                "Zone": instance.get("clusterId"),
                "OsName": instance.get("computerName"),
                "CPU": instance.get("VCpu"),
                "Memory": instance.get("memory") / 1024,
                "CreateTime": instance.get("createTime"),
                "NetworkAddress": {"private_ip": instance.get("ip")},
                "PrivateIpAddress": instance.get("ip"),
                "SystemDisk": instance.get("systemDisk"),
                "InstanceType": instance.get("templateId"),
            })
        return instances

    @classmethod
    def template(cls, resp):
        templates = []
        for template in cls.validate_empty(resp, set_name='templateInfoList'):
            templates.append({
                "Id": template.get("templateId"),
                "Name": template.get("templateName"),
                "Zone": template.get("clusterId"),
                "CPU": template.get("cores"),
                "Memory": template.get("memory") / 1024,
                "Disks": template.get("diskList"),
                "Nics": template.get("nicList"),
                "Datastores": template.get("datastoreIdList")
            })
        return templates

    @classmethod
    def datastore_by_template(cls, resp):
        datastores = []
        datastore_ids = []
        for ava_datastore in cls.validate_empty(resp, set_name='availDatastoreList'):
            for datastore in ava_datastore.get("datastoreList"):
                if datastore.get("datastoreId") not in datastore_ids:
                    datastores.append({
                        "Id": datastore.get("datastoreId"),
                        "Name": datastore.get("name")
                    })
                    datastore_ids.append(datastore.get("datastoreId"))
        return datastores

    @classmethod
    def datastore(cls, resp):
        datastores = []
        for datastore in cls.validate_empty(resp, set_name='datastoreList'):
            datastores.append({
                "Id": datastore.get("datastoreId"),
                "Name": datastore.get("name")
            })
        return datastores

    @classmethod
    def securitygroup(cls, resp):
        securitygroups = []
        for securitygroup in cls.validate_empty(resp, set_name='securityGroups'):
            securitygroups.append({
                "Id": securitygroup.get("sgId"),
                "Name": securitygroup.get("sgName"),
                "SecurityGroupDesc": securitygroup.get("sgDesc"),
                "Rule": securitygroup.get("rules")
            })
        if not securitygroups:  # fake security for test
            return [{
                "Id": 1,
                "Name": "fake-securitygroup",
                "SecurityGroupDesc": "fake-test",
                "Rule": "0.0.0.0/0"
            }]
        return securitygroups

    @classmethod
    def portgroup(cls, resp):
        portgroups = []
        for portgroup in cls.validate_empty(resp, set_name='portGroups'):
            portgroups.append({
                "Id": portgroup.get("portGroupId"),
                "Name": portgroup.get("portGroupName"),
                "dvSwitchId": portgroup.get("dvSwitchId"),
                "description": portgroup.get("description"),
                "vlanId": portgroup.get("vlanId")
            })
        return portgroups
