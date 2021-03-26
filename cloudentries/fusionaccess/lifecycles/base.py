# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.connector import Connector
from .client import FusionAccessConnect


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()
        self.connection = FusionAccessConnect(**self.connection_config)

    def get_client(self):
        try:
            client = self.connection
            return client
        except Exception as e:
            raise NonRecoverableError("Connection to  fusionaccess failed! the error message is {0}".format(e))
