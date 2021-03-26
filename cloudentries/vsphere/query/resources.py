# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from .client import VSphereClient

from pyVmomi import vim


class VSphereResource(object):

    def __init__(self, config):
        self.client = VSphereClient().create_client(config)
        self.content = self.client.RetrieveContent()

    def get_instances(self, params):

        vim_type = [vim.VirtualMachine]

        container_view = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vim_type, True)
        objects = container_view.view
        container_view.Destroy()
        res = []
        for server_id in params:
            for obj in objects:
                if server_id == obj._moId:
                    instance = {'id': str(obj._moId),
                                'name': str(obj.name),
                                'status': str(obj.guest.guestState)}
                    res.append(instance)

        return res
