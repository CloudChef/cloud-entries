# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common.utils import format_ins_status, validate_parameter
from abstract_plugin.platforms.common.compute import CommonCompute
from .base import Base
from . import constants


class Compute(Base, CommonCompute):
    def __init__(self):
        super(Compute, self).__init__()
        self.action_mapper = {
            "resize": self.resize,
            "modify_display_name": self.modify_display_name,
            "create_snapshot": self.create_snapshot,
            "delete_snapshot": self.delete_snapshot,
            "restore_snapshot": self.restore_snapshot
        }
        self.conn = self.get_client()

    def create(self):
        if self._use_external_resource():
            return True
        create_ret = self._create()
        task_id = create_ret.get("taskId")
        job_info = self.wait_job_complete(task_id)
        instance_id = job_info.get("entity")
        self.wait_for_target_state(instance_id, (constants.INSTANCE_STATE_AVAILABLE, constants.INSTANCE_STATE_STARTED))
        self.update_runtime_properties(instance_id)
        return

    def _use_external_resource(self):
        if not self.use_external_resource:
            return False
        resource_id = self.node_properties.get('resource_id')
        self.update_runtime_properties(resource_id)
        return True

    def _create(self):
        params = self.prepare_params()
        url = "/fastProvision"
        ctx.logger.info('Creating VM params: {}.'.format(params))
        create_ret = self.conn.common_request("post", url, params)
        return create_ret

    def delete(self):
        vm_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        ctx.logger.info('Stopping FusionAccess VM {}.'.format(vm_id))
        self.detach_user(vm_id)  # 解除关联的用户
        params = {
            "vmMarkList": [
                {
                    "siteId": self.resource_config.get('region'),
                    "vmId": vm_id
                }
            ],
        }
        url = "/deleteInstances"
        self.conn.common_request("post", url, params)
        ctx.instance.runtime_properties = {}
        ctx.instance.update()
        ctx.logger.info('Stopped FusionAccess VM {}.'.format(vm_id))

    def start(self):
        vm_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        ctx.logger.info('Staring FusionAccess VM {}.'.format(vm_id))
        if self.get_vm_status(vm_id) in (constants.INSTANCE_STATE_AVAILABLE, constants.INSTANCE_STATE_STARTED):
            return
        params = {
            "vmMarkList": [
                {
                    "siteId": self.resource_config.get('region'),
                    "vmId": vm_id
                }
            ]
        }
        url = "/runInstances"
        self.conn.common_request("post", url, params)
        self.wait_for_target_state(vm_id, target_state=(constants.INSTANCE_STATE_AVAILABLE,
                                                        constants.INSTANCE_STATE_STARTED))
        self.update_runtime_properties(vm_id)
        return

    def stop(self):
        vm_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        ctx.logger.info('Stopping FusionAccess VM {}.'.format(vm_id))
        params = {
            "vmMarkList": [
                {
                    "siteId": self.resource_config.get('region'),
                    "vmId": vm_id
                }
            ],
            "isForceStop": True
        }
        url = "/stopInstances"
        self.conn.common_request("post", url, params)
        self.wait_for_target_state(vm_id, (constants.INSTANCE_STATE_STOPPED,))
        ctx.logger.info('Stopped FusionAccess VM {}.'.format(vm_id))

    def reboot(self):
        vm_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        ctx.logger.info('Rebooting FusionAccess VM {}.'.format(vm_id))
        params = {
            "vmMarkList": [
                {
                    "siteId": self.resource_config.get('region'),
                    "vmId": vm_id
                }
            ],
            "isForceReboot": True
        }
        url = "/rebootInstances"
        self.conn.common_request("post", url, params)
        self.wait_for_target_state(vm_id, (constants.INSTANCE_STATE_AVAILABLE, constants.INSTANCE_STATE_STARTED))
        ctx.logger.info('Rebooted FusionAccess VM {}.'.format(vm_id))

    def resize(self, **kwargs):
        """
        调整云主机规格
        """
        vm_id = ctx.instance.runtime_properties.get(constants.EXTERNAL_ID)
        ctx.logger.info('Resize FusionAccess VM {}.'.format(vm_id))

        new_cores = kwargs.get("cpus")
        new_mem = kwargs.get("memory")
        params = {
            "updateInfoList": [{
                "vmMark": {
                    "siteId": self.resource_config.get('region'),
                    "vmId": vm_id
                },
                "cores": new_cores,
                "memory": new_mem
            }]
        }
        url = "/updateInstances"
        self.conn.common_request("post", url, params)
        ctx.logger.info('Resize FusionAccess VM {}.'.format(vm_id))

    def modify_display_name(self):
        """
        修改云主机名称
        """
        pass

    def create_snapshot(self):
        """
        创建快照
        """
        pass

    def delete_snapshot(self):
        """
        删除快照
        """
        pass

    def restore_snapshot(self):
        """
        恢复快照
        """
        pass

    def wait_for_target_state(self, instance_id, target_state=("running",), timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            instance_state = self.get_vm_status(instance_id)
            ctx.logger.info('Waiting for server "{0}" to be {1}. current state: {2}'
                            .format(instance_id, target_state, instance_state))
            if isinstance(target_state, tuple):
                if instance_state in target_state:
                    return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting for server to be target state failed! the current "
                                  "state is {0}, the target state is {1}".format(instance_state, target_state))

    def update_runtime_properties(self, instance_id):
        vm = self.describe_vm(instance_id)
        vm_status = self.get_vm_status(instance_id)  # get vm_status from vm
        ctx.instance.runtime_properties.update({
            'external_id': instance_id,
            'external_hostname': vm.get("computerName"),
            'external_name': vm.get("computerName"),
            'status': vm_status,  # need transfer vm_status to common status
            'vm_info': vm})
        self.set_ip_info(vm)
        ctx.instance.update()

    def set_ip_info(self, vm_info):
        net_info = {}  # get net_info from vm_info
        ip_address = vm_info.get("ip", "")  # get ip_address from net_info
        network_info = {'ip': ip_address, 'name': 'PrivateIpAddress'}
        ctx.instance.runtime_properties['ip'] = ip_address
        if self.use_external_resource:
            # There is not network connected to instance,instance is external.
            ctx.instance.runtime_properties['networks'] = {'Network': network_info}
        else:
            # Create by CMP.
            related_network = self.get_primary_network()
            networks_runtime = ctx.instance.runtime_properties.get('networks')
            networks_runtime[related_network.node.id].update(network_info)
        if net_info.get('PublicIp'):
            public_ip = net_info.get('PublicIp')
            public_ip_info = {
                'name': 'public_ip',
                'ip': public_ip
            }
            ctx.instance.runtime_properties['networks'].update({'public_ip': public_ip_info})
            ctx.instance.runtime_properties['ip'] = public_ip
        ctx.instance.update()

    def prepare_params(self):
        # change key-value according to concrete cloud api
        template_id = validate_parameter('image_id', self.resource_config)
        login_id = validate_parameter('login_id', self.resource_config)
        memory = self.resource_config.get('mem') * 1024 if self.resource_config.get('mem') \
            else self._template_mem(template_id)
        params = {
            'resourceGroupName': constants.resourceGroupName,
            'resourceGroupType': constants.resourceGroupType,
            'farmId': constants.farmId,
            'templateId': template_id,
            'name': self.resource_config.get('name') or ctx.instance.id,
            'cores': self.resource_config.get('cpu') or self._template_cpu(template_id),
            'memory': memory,  # MB
            'diskList': self._template_disks(template_id),
            'instanceNum': 1,
            'siteId': self.resource_config.get('region'),
            'galaxVersion': constants.galaxVersion,
            'clusterId': self.resource_config.get('available_zone_id'),
            'dgName': constants.dgName,
            'dgType': constants.dgType,
            'namingPolicy': constants.namingPolicy,
            'domain': constants.domain,
            'isMacBind': 1
        }
        new_params = self.update_network_params(params, login_id)
        return new_params

    def describe_template(self, template_id):
        params = {
            "siteId": self.region,
            "clusterId": self.zone
        }
        url = "/describeTemplatesInfo"
        try:
            res = self.conn.common_request("post", url, params)
            templates_info = res.get("templateInfoList", [])
            if not templates_info:
                return {}
            for template in templates_info:
                if template.get("templateId") == template_id:
                    return template
            return {}
        except Exception as e:
            raise NonRecoverableError("Failed to describe template: {}, the error message is {}".format(template_id, e))

    def _template_cpu(self, template_id):
        template = self.describe_template(template_id)
        if not template:
            return ""
        return template.get("cores")

    def _template_mem(self, template_id):
        template = self.describe_template(template_id)
        if not template:
            return ""
        return template.get("memory")

    def _template_disks(self, template_id):
        template = self.describe_template(template_id)
        if not template:
            return ""
        return template.get("diskList")

    def get_networks(self):
        networks = super(Compute, self).get_networks()
        return networks

    def _template_nics(self):
        nic_info = []
        networks = self.get_networks()
        for network in networks:
            network_info = network.instance.runtime_properties['network']
            nic_info.append({
                "dvSwitchId": network_info.get("switch_id"),
                "portGroupId": network_info.get("id")
            })
        return nic_info

    def update_network_params(self, create_params, login_id):
        nic_info = []
        ip_allocation_method = ""
        network_nodes = self.get_networks()
        for network in network_nodes:
            net_runtimes = network.instance.runtime_properties['network']
            nic_info.append({
                "dvSwitchId": str(net_runtimes.get("switch_id")),
                "portGroupId": str(net_runtimes.get("id"))
            })
            ip_allocation_method = network.instance.runtime_properties.get("ip_allocation_method")
        create_params.update({
            "nicList": nic_info
        })
        network_info = self.get_network_info()
        ctx.logger.info('Network Params: {}.'.format(network_info))
        user_info = {
            "userList": [
                login_id
            ],
            "role": "administrators",
            "attachType": "Private"
        }
        if ip_allocation_method == "DHCP":
            create_params.update({
                "ipMod": "0"
            })
        else:
            dns_servers = network_info.get("dns_servers")
            static_ip_info = {
                "netMask": network_info.get("netmask"),
                "netGate": network_info.get("gateway"),
                "dnsPramary": dns_servers[0],
                "ipForResourceGroup": [network_info.get("ip")],
            }
            if len(dns_servers) > 1:
                static_ip_info.update({
                    "dnsSecond": dns_servers[1]
                })
            create_params.update({
                "ipMod": "1",
                "staticIpInfo": static_ip_info
            })
            user_info.update({"ipAddress": network_info.get("ip")})
        create_params.update({"userInfoList": [user_info]})
        return create_params

    def describe_vm(self, instance_id):
        params = {
            "siteId": self.region,
            "instanceId": instance_id
        }
        url = "/describeInstanceDetail"
        try:
            res = self.conn.common_request("post", url, params)
            return res.get("instanceDetailInfo")
        except Exception as e:
            raise NonRecoverableError("Failed to describe vm: {}, the error message is {}".format(instance_id, e))

    def get_vm_status(self, instance_id):
        vm_info = self.describe_vm(instance_id)
        if not vm_info:
            return ""
        return format_ins_status(vm_info.get("instanceState"))

    def detach_user(self, instance_id):
        attach_infos = self.get_vm_attachuser(instance_id)
        attach_users = []
        for attach_info in attach_infos:
            if attach_info.get("userOrGroupName"):
                attach_users.append(attach_info.get("userOrGroupName"))
        params = {
            "vmMark": {
                "siteId": self.resource_config.get('region'),
                "vmId": instance_id
            },
            "userNameList": attach_users
        }
        url = "/delUserFromVm"
        return self.conn.common_request("post", url, params)

    def get_vm_attachuser(self, instance_id):
        vm_info = self.describe_vm(instance_id)
        if not vm_info:
            return ""
        return vm_info.get("vmAttachInfoList")

    def wait_job_complete(self, task_id, target_job_status="SUCCESS", timeout=1200, sleep_interval=30):
        timeout = time.time() + timeout
        while time.time() < timeout:
            job_info = self.conn.describe_job(task_id)
            if not job_info:
                raise NonRecoverableError('Describe job info:{} failed, msg:{}'.format(task_id, job_info))
            job_status = job_info.get("status")
            ctx.logger.info('Waiting for job:{0} status to be {1}. current state is: {2}'
                            .format(task_id, target_job_status, job_status))
            if job_status == target_job_status:
                return job_info
            elif job_status == "FAILED":
                raise NonRecoverableError('Describe job:{} status is failed, msg:{}'.format(task_id, job_info))
            time.sleep(sleep_interval)
        raise NonRecoverableError('Waiting for job:{0} status to be {1}. current state is: {2}'.
                                  format(task_id, target_job_status, job_status))
