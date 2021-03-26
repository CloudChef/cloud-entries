# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify import ctx
from abstract_plugin.platforms.common.connector import Connector
from abstract_plugin.platforms.common.constants import (
    EXTERNAL_ID,
    EXTERNAL_NAME
)


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()

    def wait_job(self, helper, job_id, resource_type='KVM_VM'):
        helper.wait_job(job_id)
        job_detail = helper.get_job(job_id)

        resource_id = None

        if job_detail['state'] == 'failed':
            raise Exception(job_detail['task_list'])

        job_resources = job_detail['resources']
        for key in list(job_resources.keys()):
            if job_resources[key]['type'].startswith(resource_type):
                resource_id = key
                break

        return resource_id

    def set_optional_values(self, source, target, optional_keys):
        for item in optional_keys:

            if item == 'cpu' and (source.get('cores') and source.get('sockets')):
                cpu = {
                    'topology': {
                        'cores': source.get('cores'),
                        'sockets': source.get('sockets')
                    }
                }
                target['cpu'] = cpu
            elif item == 'node_ip':
                node_ip = source.get('node_ip')
                if node_ip:
                    auto_schedule = False
                    target['node_ip'] = node_ip
                else:
                    auto_schedule = True
                target['auto_schedule'] = auto_schedule
            elif item == 'storage_policy_uuid' and source.get('volume_type'):
                target['storage_policy_uuid'] = source.get('volume_type')
            elif source.get(item):
                target[item] = source[item]

    def save_runtime_properties(self, resource_type, info=None, extra_values={}):

        if info:
            info_key = '_'.join([resource_type, 'info'])
            required_values = {
                EXTERNAL_ID: info.get('uuid'),
                EXTERNAL_NAME: info.get('name') or info.get('vm_name'),
                info_key: info
            }
            ctx.instance.runtime_properties.update(required_values)

        ctx.instance.runtime_properties.update(extra_values)
