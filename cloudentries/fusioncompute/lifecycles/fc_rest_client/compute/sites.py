# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from ..common import FusionComputeBase


class SitesClient(FusionComputeBase):
    SITES_URI = '/service/sites'

    def list(self):
        uri = self.SITES_URI
        return self.rest_client.get(uri)
