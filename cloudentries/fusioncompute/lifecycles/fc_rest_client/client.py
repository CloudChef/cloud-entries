# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from requests.packages import urllib3
import hashlib

from .auth import Auth
from .common import RestClient
from .compute import (
    SitesClient,
    ClustersClient,
    HostsClient,
    ServersClient)
from .network import (
    DvSwitchsClient,
    PortGroupsClient,
    SecurityGroupClient)
from .storage import DatastoresClient, VolumesClient

DEFAULT_API_VERSION = '6.3'

urllib3.disable_warnings(urllib3.exceptions.InsecurePlatformWarning)


class FusionComputeClient(object):
    """FusionCompute management client."""
    client_class = RestClient

    def __init__(self, auth_url=None, username=None,
                 password=None, verify=False, cert=None,
                 api_version=DEFAULT_API_VERSION):
        auth = Auth(base_url=auth_url,
                    username=username,
                    password=self.encrypt(password),
                    verify=verify,
                    cert=cert,
                    version=api_version)

        self._client = self.client_class(auth=auth,
                                         verify=verify,
                                         cert=cert)
        self.sites = SitesClient(self._client)
        self.clusters = ClustersClient(self._client)
        self.hosts = HostsClient(self._client)
        self.servers = ServersClient(self._client)
        self.dvswitchs = DvSwitchsClient(self._client)
        self.portgroups = PortGroupsClient(self._client)
        self.datastores = DatastoresClient(self._client)
        self.volumes = VolumesClient(self._client)
        self.securitygroups = SecurityGroupClient(self._client)

    @staticmethod
    def encrypt(password):
        sha256 = hashlib.sha256()
        sha256.update(password.encode('utf-8'))
        return sha256.hexdigest()
