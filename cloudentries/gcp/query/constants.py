# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

GCP_PUBLIC_PROJECT = {
    'centos-cloud': ['centos-6', 'centos-7', 'centos-8'],
    'cos-cloud': ['cos-65-lts', 'cos-69-lts', 'cos-73-lts', 'cos-77-lts', 'cos-81-lts', 'cos-beta', 'cos-dev',
                  'cos-stable'],
    'debian-cloud': ['debian-7-backports', 'debian-10', 'debian-7', 'debian-8', 'debian-9'],
    'rhel-cloud': ['rhel-6', 'rhel-7', 'rhel-8'],
    'suse-cloud': ['sles-12', 'sles-15'],
    'windows-cloud': ['windows-1709-core-for-containers', 'windows-1709-core', 'windows-1803-core-for-containers',
                      'windows-1803-core', 'windows-1809-core-for-containers', 'windows-1809-core-gke',
                      'windows-1809-core', 'windows-1903-core-for-containers', 'windows-1903-core',
                      'windows-1909-core-for-containers',
                      'windows-1909-core', 'windows-2008-r2', 'windows-2012-r2-core', 'windows-2012-r2',
                      'windows-2016-core', 'windows-2016',
                      'windows-2019-core-for-containers', 'windows-2019-core', 'windows-2019-for-containers',
                      'windows-2019']
}

REGION_MAPPER = {
    "id": "Id",
    "name": "Name"
}

ZONE_MAPPER = {
    "id": "Id",
    "name": "Name",
    "region": "RegionId"
}

NETWORK_MAPPER = {
    "id": "Id",
    "name": "Name"
}

PORTGROUPS_MAPPER = {
    "id": "Id",
    "name": "Name",
    "network": "NetworkId",
    'ipCidrRange': 'Cidr'
}

INSTANCE_MAPPER = {
    "id": "Id",
    "name": "Name",
    "status": "Status"
}

SECURITY_GROUP_MAPPER = {
    "id": "Id",
    "name": "Name"
}

FLAVOR_MAPPER = {
    "id": "Id",
    "name": "Name"
}

VOLUME_MAPPER = {
    "id": "Id",
    "name": "Name"
}

VOLUME_TYPE_MAPPER = {
    "id": "Id",
    "name": "Name"
}

VM_DISK_MAPPER = {
    "id": "Id",
    "deviceName": "Name"
}
