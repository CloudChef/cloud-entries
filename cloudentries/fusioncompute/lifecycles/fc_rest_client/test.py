# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import json
from .client import FusionComputeClient

auth_url = ""
user = ""
password = ""
fc_client = FusionComputeClient(auth_url=auth_url,
                                username=user,
                                password=password)
sites = fc_client.sites.list()
print(json.dumps(sites, indent=2))
site = fc_client.sites.get('48630826')
print(json.dumps(site, indent=2))
vms = fc_client.servers.list('48630826')
print(json.dumps(vms, indent=2))

hosts = fc_client.hosts.list('48630826')
print(json.dumps(hosts, indent=2))

datastores = fc_client.datastores.list('48630826')
print(json.dumps(datastores, indent=2))

vm = fc_client.servers.get('48630826', 'i-0000000E')
print(json.dumps(vm, indent=2))

dvswitchs = fc_client.dvswitchs.list('48630826')
print(json.dumps(dvswitchs, indent=2))

portgroups = fc_client.portgroups.list('48630826', '1')
print(json.dumps(portgroups, indent=2))

clone_config = {
    "name": "xftest",
    "group": "",
    "location": "urn:sites:48630826:hosts:356",
    "isBindingHost": False,
    "vmConfig":
        {
            "cpu":
                {
                    "quantity": 4,
                },
            "memory":
                {
                    "quantityMB": 1024 * 16,
                },
            "disks":
                [
                    {
                        "systemVolume": True,
                        "sequenceNum": 1,
                        "isDataCopy": True,
                        "quantityGB": 120,
                        "datastoreUrn": "urn:sites:48630826:datastores:3",
                        "isThin": True,
                    }
                ],
        },
    "autoBoot": True,
    "isTemplate": False,
}

clone_result = fc_client.servers.clone('48630827', 'i-0000000B', clone_config)
print(clone_result)
