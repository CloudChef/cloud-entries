# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import ssl

import atexit
import time

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


class VSphereClient(object):

    def connect(self, auth_params):
        context = None
        if hasattr(ssl, '_create_unverified_context'):
            context = ssl._create_unverified_context()
        for i in range(6):
            try:
                self.si = SmartConnect(
                    host=auth_params.get('host'),
                    user=auth_params.get('user'),
                    pwd=auth_params.get('password'),
                    port=int(auth_params.get('port')),
                    sslContext=context)
                atexit.register(Disconnect, self.si)
            except vim.fault.InvalidLogin:
                time.sleep(10)
            else:
                break
        else:
            raise Exception(
                'Could not login to VSphere {} with provided credentials '
                'in 60s.'.format(auth_params.get('host')))

    def create_client(self, auth_params):
        self.connect(auth_params)
        return self.si
