# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import validate_parameter
from cloudify.utils import decrypt_password
from .fc_rest_client.client import FusionComputeClient


class FusionCompute(object):
    def __init__(self, params):
        self.auth_url = validate_parameter('base_url', params)
        self.username = validate_parameter('username', params)
        self.password = decrypt_password(validate_parameter('password', params))

    def connection(self):
        try:
            fc_client = FusionComputeClient(auth_url=self.auth_url,
                                            username=self.username,
                                            password=self.password)
            return fc_client
        except Exception as e:
            ctx.logger.info(" ")
            raise NonRecoverableError("Connect to FusionCompute failed! The error message is {}".format(e))
