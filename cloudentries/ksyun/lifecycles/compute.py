# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
import os
import copy
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password
from abstract_plugin.platforms.common.utils import validate_parameter
import abstract_plugin.platforms.common.constants as common_constants
from .base import Base
from .handler import client_error_handler
from abstract_plugin.platforms.common.compute import CommonCompute
from abstract_plugin.platforms.ksyun.restclient import Helper
from . import constants as ksyun_constants


class Compute(Base, CommonCompute):
    def __init__(self):
        super(Compute, self).__init__()
        self.action_mapper = {
            "create_snapshot": self.create_snapshot,
            "restore_snapshot": self.restore_snapshot,
            "delete_snapshot": self.delete_snapshot,
            "modify_display_name": self.modify_display_name,
            "resize": self.resize
        }

    def prepare_params(self):
        nsg_id = self.get_nsg_id()

        if not nsg_id:
            raise NonRecoverableError("Can not get security group id, please set in environment variable, "
                                      "the environment variable key is 'KSYUN_NSG'.")

        instance_name = self.resource_config.get('instance_name')
        hostname = None
        if not instance_name:
            instance_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or instance_name

        if self.resource_config.get('instance_name'):
            instance_name = self.resource_config.get('instance_name')
        else:
            instance_name, hostname = self.get_instance_names()

        params_info = {
            'ImageId': validate_parameter('image_id', self.resource_config),
            'InstanceType': validate_parameter('flavor', self.resource_config),
            'SubnetId': self.get_subnet(),
            'MaxCount': 1,
            'MinCount': 1,
            'SecurityGroupId': nsg_id,
            'InstancePassword': decrypt_password(validate_parameter('password', self.resource_config)),
            'InstanceName': instance_name,
            'ChargeType': self.resource_config.get('charge_type') or 'HourlyInstantSettlement',
            'PurchaseTime': self.resource_config.get('purchase_time') or 0,
            'SystemDisk.DiskType': self.resource_config.get('system_disk_config').get('volume_type'),
            'SystemDisk.DiskSize': self.resource_config.get('system_disk_config').get('size')
        }
        if hostname:
            params_info['HostName'] = hostname
        if os.environ.get('KSYUN_SYSTEM_DISK_TYPE'):
            params_info.update({
                'SystemDisk.DiskType': os.environ.get('KSYUN_SYSTEM_DISK_TYPE'),
                'SystemDisk.DiskSize': int(os.environ.get('KSYUN_SYSTEM_DISK_SIZE'))})

        ip_address = self.get_ip()
        if ip_address:
            ip_address_info = {
                'PrivateIpAddress': ip_address
            }
            params_info.update(ip_address_info)

        return params_info

    def describe_vm(self, instance_id):
        res = Helper().execute_request('kec', 'describe_instances', {"InstanceId.1": instance_id})
        return None if not res.get("InstancesSet") else res['InstancesSet'][0]

    def get_vm_state(self, instance_id):
        vm_info = self.describe_vm(instance_id)
        return None if not vm_info else vm_info['InstanceState']['Name']

    def wait_for_target_state(self, instance_id, target_state, timeout=600, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            instance_state = self.get_vm_state(instance_id)
            ctx.logger.info('Waiting for server "{0}" to be {1}. current state: {2}'
                            .format(instance_id, target_state, instance_state))
            if isinstance(target_state, tuple):
                if instance_state in target_state:
                    return
            else:
                if instance_state == target_state:
                    return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting server to target state failed! the current "
                                  "state is {0}, the target state is {1}".format(instance_state, target_state))

    def update_runtime_properties(self, instance_id):
        vm = self.describe_vm(instance_id)
        raw_status = vm['InstanceState']['Name']
        vm_status = ksyun_constants.KS_INSTANCE_STATE_CONVERT.get(raw_status, raw_status)
        ctx.instance.runtime_properties.update({
            common_constants.EXTERNAL_ID: vm.get('InstanceId'),
            common_constants.EXTERNAL_NAME: vm.get('InstanceName'),
            'external_hostname': vm.get('HostName'),
            'VpcId': vm.get('NetworkInterfaceSet', [{}])[0].get('VpcId'),
            'network_interface_id': vm['NetworkInterfaceSet'][0]['NetworkInterfaceId'],
            'vm_info': vm,
            'status': vm_status
        })
        self.set_ip_info(vm)
        ctx.instance.update()

    def set_ip_info(self, vm_info):
        net_info = vm_info['NetworkInterfaceSet'][0]
        network_info = {'ip': net_info.get('PrivateIpAddress'), 'name': 'PrivateIpAddress'}
        ctx.instance.runtime_properties['ip'] = net_info.get('PrivateIpAddress')
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
        ips = []
        if net_info.get('PublicIp'):
            ips.append(net_info.get('PublicIp'))
        ips.append(net_info.get('PrivateIpAddress'))
        ctx.instance.runtime_properties['ips'] = ips
        ctx.instance.update()

    def _create(self):
        params = self.prepare_params()
        display_params = copy.deepcopy(params)
        ctx.instance.runtime_properties[common_constants.EXTERNAL_HOSTNAME] = params.get('HostName')
        display_params['InstancePassword'] = '********'
        ctx.logger.info("VM creating params is {0}".format(display_params))
        return Helper().execute_request('kec', 'run_instances', params)['InstancesSet'][0]['InstanceId']

    def create(self):
        if self.use_external_resource is True:
            instance_id = validate_parameter('resource_id', self.node_properties)
        else:
            instance_id = self._create()
            self.wait_for_target_state(instance_id, ksyun_constants.KS_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)
        self.associate_eip()

    def is_allocated_eip(self):
        eip_node = self.get_eip_node()
        if eip_node and eip_node.properties.get('resource_config').get('allocate_eip'):
            return True
        return False

    def associate_eip(self):
        if not self.is_allocated_eip():
            return
        eip_obj = self.get_eip()
        vm = ctx.instance
        eip_id = eip_obj.runtime_properties[common_constants.EXTERNAL_ID]
        instance_id = vm.runtime_properties[common_constants.EXTERNAL_ID]
        interface_id = vm.runtime_properties['network_interface_id']
        ctx.logger.info(
            'Start associate EIP:{} to Instance:{},interface_id:{}'.format(eip_id, instance_id, interface_id))
        request_body = {
            'AllocationId': eip_id,
            'InstanceId': instance_id,
            'InstanceType': 'Ipfwd',
            'NetworkInterfaceId': interface_id
        }
        Helper().execute_request('eip', 'associate_address', request_body)
        eip_obj = self.wait_eip_for_target_state(eip_id, [ksyun_constants.KS_EIP_STATE_ASSOCIATE])
        networks = vm.runtime_properties['networks']
        networks['public_ip'] = {'ip': eip_obj['PublicIp'], 'name': 'public_ip'}
        vm.runtime_properties['networks'] = networks
        vm.runtime_properties['ip'] = eip_obj['PublicIp']
        ctx.instance.update()
        self.update_eip_runtime()
        ctx.logger.info('Associate EIP successfully...')

    def disassociate_eip(self):
        if not self.is_allocated_eip():
            return
        eip_obj = self.get_eip()
        eip_id = eip_obj.runtime_properties[common_constants.EXTERNAL_ID]
        ctx.logger.info('Disassociate EIP id:{}'.format(eip_id))
        request_body = {
            'AllocationId': eip_id
        }
        ctx.logger.info('Start to disassociate EIP:{}...'.format(eip_id))
        Helper().execute_request('eip', 'disassociate_address', request_body)
        self.wait_eip_for_target_state(eip_id, [ksyun_constants.KS_EIP_STATE_DISASSOCIATE])
        vm = ctx.instance
        networks = vm.runtime_properties['networks']
        networks.pop('public_ip')
        vm.runtime_properties['networks'] = networks
        vm_info = self.describe_vm(vm.runtime_properties[common_constants.EXTERNAL_ID])
        if vm_info:
            vm.runtime_properties['ip'] = vm_info['PrivateIpAddress']
        vm.update()
        self.update_eip_runtime()
        ctx.logger.info('Disassociate EIP successfully...')

    def wait_eip_for_target_state(self, eip_id, statuses, timeout=600, interval=15):
        request_body = {
            'AllocationId.1': eip_id
        }
        eip_info = Helper().execute_request('eip', 'describe_addresses', request_body)['AddressesSet'][0]
        while timeout:
            if eip_info['State'] in statuses:
                return eip_info
            ctx.logger.info(
                'Wait Eip:{} to be status:{},current status:{}...'.format(eip_id, ','.join(statuses),
                                                                          eip_info['State']))
            time.sleep(interval)
            timeout -= interval
        raise NonRecoverableError("Waiting eip to target state failed! the current "
                                  "state is {0}, the target state:{1}".format(eip_info['State'], ','.join(statuses)))

    def update_eip_runtime(self):
        eip_instance = self.get_eip()
        eip_id = eip_instance.runtime_properties[common_constants.EXTERNAL_ID]
        eip_instance.runtime_properties = {}
        request_body = {
            'AllocationId.1': eip_id
        }
        eip_info = Helper().execute_request('eip', 'describe_addresses', request_body)['AddressesSet'][0]
        eip_instance.runtime_properties[common_constants.EXTERNAL_ID] = eip_info['AllocationId']
        eip_instance.runtime_properties[common_constants.EIP_ADDRESS] = eip_info['PublicIp']
        eip_instance.runtime_properties[common_constants.EIP_STATUS] = eip_info['State']
        eip_instance.runtime_properties[ksyun_constants.KS_EIP_TYPE] = eip_info.get('InstanceType')
        instance_id = eip_info.get('InstanceId')
        if instance_id and eip_info.get('InstanceType') == 'Ipfwd':
            vm_info = self.describe_vm(eip_info['InstanceId'])
            if vm_info:
                eip_instance.runtime_properties[common_constants.EIP_RELATED_INSTANCE_ID] = eip_info['InstanceId']
                eip_instance.runtime_properties[common_constants.EIP_RELATED_INSTANCE_NAME] = vm_info.get(
                    'InstanceName')
        eip_instance.update()

    def _start(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == ksyun_constants.KS_INSTANCE_STATE_ACTIVE:
            ctx.logger.info("The virtual machine is active, No need to start!")
            return
        if vm_state != ksyun_constants.KS_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Only virtual machines that are in a stopped state can be started")
        else:
            Helper().execute_request('kec', 'start_instances', {"InstanceId.1": instance_id})

    def start(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._start(instance_id)
        self.wait_for_target_state(instance_id, ksyun_constants.KS_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)

    def _stop(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if not vm_state:
            ctx.logger.info("The virtual machine isnot exist, No need to stop!")
            return "not exist"
        if vm_state == ksyun_constants.KS_INSTANCE_STATE_STOPPED:
            ctx.logger.info("The virtual machine is stopped, No need to stop!")
            return
        stop_params = {
            "InstanceId.1": instance_id,
            "ForceStop": True,
            "StoppedMode": "StopCharging"}
        Helper().execute_request('kec', 'stop_instances', stop_params)

    def stop(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        if self._stop(instance_id) == "not exist":
            return
        self.wait_for_target_state(instance_id, ksyun_constants.KS_INSTANCE_STATE_STOPPED)
        self.update_runtime_properties(instance_id)

    def _reboot(self, instance_id):
        vm_state = self.get_vm_state(instance_id)
        if vm_state == ksyun_constants.KS_INSTANCE_STATE_STOPPED:
            raise NonRecoverableError("Can not reboot virtual machine which state is stopped, you can start it!")
        reboot_params = {
            'InstanceId.1': instance_id,
            'ForceReboot': True}
        Helper().execute_request('kec', 'reboot_instances', reboot_params)

    def reboot(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self._reboot(instance_id)
        self.wait_for_target_state(instance_id, ksyun_constants.KS_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(instance_id)

    def delete(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self.disassociate_eip()
        Helper().execute_request('kec', 'terminate_instances', {"InstanceId.1": instance_id})
        self.release_ip_in_delete_operation()
        time.sleep(os.environ.get("KSYUN_VM_DELETE_WAIT_TIME_SECOND") or 5)

    def process_external_resource(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        self.update_runtime_properties(instance_id)

    def describe_instance_local_volumes(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        local_volumes = Helper().execute_request('kec', 'describe_local_volumes', {"InstanceId": instance_id})
        local_volumes = local_volumes.get('LocalVolumeSet') or []
        return local_volumes

    def describe_instance_cloud_volumes(self):
        instance_id = ctx.instance.runtime_properties['external_id']
        cloud_volumes = Helper().execute_request('ebs', 'describe_instance_volumes', {"InstanceId": instance_id})
        cloud_volumes = cloud_volumes.get('Attachments') or []
        return cloud_volumes

    @client_error_handler
    def describe_local_volume_snapshot_by_id(self, snapshot_id):
        snapshot = \
            Helper().execute_request('kec', 'describe_local_volume_snapshots',
                                     {'LocalVolumeSnapshotId': snapshot_id}).get('LocalVolumeSnapshotSet')[0]
        return snapshot

    @client_error_handler
    def describe_cloud_volume_snapshot_by_id(self, snapshot_id):
        snapshot = Helper().execute_request('ebs', 'describe_snapshots',
                                            {'SnapshotId': snapshot_id}).get('Snapshots')[0]
        return snapshot

    def get_local_volume_snapshot_state(self, snapshot_id):
        snapshot = self.describe_local_volume_snapshot_by_id(snapshot_id)
        return snapshot['State']

    def get_cloud_volume_snapshot_state(self, snapshot_id):
        snapshot = self.describe_cloud_volume_snapshot_by_id(snapshot_id)
        return snapshot['SnapshotStatus']

    def wait_for_snapshot_available(self, snapshot_type, snapshot_id, timeout=1200, sleep_interval=10):
        timeout = time.time() + timeout
        while time.time() < timeout:
            if snapshot_type == 'local_volume':
                snapshot_state = self.get_local_volume_snapshot_state(snapshot_id)
                ctx.logger.info('Waiting for snapshot "{0}" to be ACTIVE. current state: {1}'
                                .format(snapshot_id, snapshot_state))
            else:
                snapshot_state = self.get_cloud_volume_snapshot_state(snapshot_id)
                ctx.logger.info('Waiting for snapshot "{0}" to be available. current state: {1}'
                                .format(snapshot_id, snapshot_state))
            if snapshot_state in ksyun_constants.KS_SNAPSHOT_STATE_AVAILABLE:
                return
            time.sleep(sleep_interval)
        raise NonRecoverableError("Waiting for snapshot available timeout({0} seconds)! the current "
                                  "state is {1}".format(timeout, snapshot_state))

    @client_error_handler
    def create_local_volume_snapshot(self, volume_id, name, desc):
        instance_id = ctx.instance.runtime_properties['external_id']
        params = {
            'LocalVolumeId': volume_id,
            'LocalVolumeSnapshotName': name,
            'LocalVolumeSnapshotDesc': desc
        }
        self.wait_for_target_state(
            instance_id,
            (ksyun_constants.KS_INSTANCE_STATE_ACTIVE, ksyun_constants.KS_INSTANCE_STATE_STOPPED))
        resp = Helper().execute_request('kec', 'create_local_volume_snapshot', params)
        self.wait_for_snapshot_available('local_volume', snapshot_id=resp['LocalVolumeSnapshotId'])

    @client_error_handler
    def create_cloud_volume_snapshot(self, volume_id, name, desc):
        instance_id = ctx.instance.runtime_properties['external_id']
        params = {
            'VolumeId': volume_id,
            'SnapshotName': name,
            'SnapshotDesc': desc
        }
        self.wait_for_target_state(
            instance_id,
            (ksyun_constants.KS_INSTANCE_STATE_ACTIVE, ksyun_constants.KS_INSTANCE_STATE_STOPPED))
        resp = Helper().execute_request('ebs', 'create_snapshot', params)
        self.wait_for_snapshot_available('cloud_volume', snapshot_id=resp['SnapshotId'])

    def create_snapshot(self, **kwargs):
        snapshot_name = kwargs.get('snapshotName')
        snapshot_description = kwargs.get('snapshotDesc') or snapshot_name
        cloud_volumes = self.describe_instance_cloud_volumes()
        for volume in cloud_volumes:
            self.create_cloud_volume_snapshot(volume['VolumeId'], snapshot_name, snapshot_description)
        local_volumes = self.describe_instance_local_volumes()
        for volume in local_volumes:
            self.create_local_volume_snapshot(volume['LocalVolumeId'], snapshot_name, snapshot_description)

    @client_error_handler
    def restore_local_volume_snapshot(self, volume_id, snapshot_id):
        params = {
            "LocalVolumeId": volume_id,
            "LocalVolumeSnapshotId": snapshot_id
        }
        Helper().execute_request('kec', 'rollback_local_volume', params)

    @client_error_handler
    def restore_cloud_volume_snapshot(self, volume_id, snapshot_id):
        params = {
            "VolumeId": volume_id,
            "SnapshotId": snapshot_id
        }
        Helper().execute_request('ebs', 'rollback_snapshot', params)

    def restore_snapshot_by_name(self, snapshot_name):
        found_snapshot = False
        cloud_volume_snapshots = self.describe_cloud_volume_snapshots()
        for snapshot in cloud_volume_snapshots:
            if snapshot['SnapshotName'] == snapshot_name:
                found_snapshot = True
                self.restore_cloud_volume_snapshot(
                    snapshot['VolumeId'],
                    snapshot['SnapshotId']
                )
                ctx.logger.info('Rollback volume {0} with snapshot {1}'.format(
                    snapshot['VolumeId'], snapshot['SnapshotId']))
        local_volume_snapshots = self.describe_local_volume_snapshots()
        for snapshot in local_volume_snapshots:
            if snapshot['LocalVolumeSnapshotName'] == snapshot_name:
                found_snapshot = True
                self.restore_local_volume_snapshot(
                    snapshot['SourceLocalVolumeId'],
                    snapshot['LocalVolumeSnapshotId']
                )
                ctx.logger.info('Rollback volume {0} with snapshot {1}'.format(
                    snapshot['SourceLocalVolumeId'], snapshot['LocalVolumeSnapshotId']))
        if not found_snapshot:
            raise NonRecoverableError('Snapshot {0} not found'.format(snapshot_name))

    def restore_snapshot(self, **kwargs):
        snapshot_name = validate_parameter('snapshotName', kwargs)
        self.restore_snapshot_by_name(snapshot_name)

    def describe_local_volume_snapshots(self):
        local_volumes = self.describe_instance_local_volumes()
        snapshots = []
        for volume in local_volumes:
            params = {'SourceLocalVolumeId': volume['LocalVolumeId']}
            volume_snapshots = Helper().execute_request('kec', 'describe_local_volume_snapshots', params).get(
                'LocalVolumeSnapshotSet') or []
            snapshots.extend(volume_snapshots)
        return snapshots

    def describe_cloud_volume_snapshots(self):
        cloud_volumes = self.describe_instance_cloud_volumes()
        snapshots = []
        for volume in cloud_volumes:
            params = {'VolumeId': volume['VolumeId']}
            volume_snapshots = Helper().execute_request('ebs', 'describe_snapshots', params).get('Snapshots') or []
            snapshots.extend(volume_snapshots)
        return snapshots

    @client_error_handler
    def delete_local_volume_snapshot(self, snapshot_id):
        params = {"LocalVolumeSnapshotId.1": snapshot_id}
        Helper().execute_request('kec', 'delete_local_volume_snapshot', params)

    @client_error_handler
    def delete_cloud_volume_snapshot(self, snapshot_id):
        params = {"SnapshotId": snapshot_id}
        Helper().execute_request('ebs', 'delete_snapshot', params)

    def delete_snapshot_by_name(self, snapshot_name):
        found_snapshot = False
        cloud_volume_snapshots = self.describe_cloud_volume_snapshots()
        for snapshot in cloud_volume_snapshots:
            if snapshot['SnapshotName'] == snapshot_name:
                found_snapshot = True
                self.delete_cloud_volume_snapshot(snapshot['SnapshotId'])
        local_volume_snapshots = self.describe_local_volume_snapshots()
        for snapshot in local_volume_snapshots:
            if snapshot['LocalVolumeSnapshotName'] == snapshot_name:
                found_snapshot = True
                self.delete_local_volume_snapshot(snapshot['LocalVolumeSnapshotId'])
        if not found_snapshot:
            raise NonRecoverableError('Snapshot {0} not found'.format(snapshot_name))

    def delete_snapshot(self, **kwargs):
        snapshots = kwargs.get('snapshots') or []
        for snapshot in snapshots:
            self.delete_snapshot_by_name(snapshot['snapshotName'])

    def _modify_display_name(self, instance_id, new_name):
        Helper().execute_request('kec', 'modify_instance_attribute',
                                 {"InstanceId": instance_id, "InstanceName": new_name})

    def modify_display_name(self, **kwargs):
        names = kwargs['names']
        instance_id = ctx.instance.id
        new_name = names.get(instance_id)
        if not new_name:
            raise NonRecoverableError(
                "Invalid args: {a} of request, node instance {b}'s 'name' is "
                "not provided.".format(a=kwargs, b=instance_id))
        vm_id = ctx.instance.runtime_properties['external_id']
        self._modify_display_name(vm_id, new_name)
        ctx.instance.runtime_properties['external_name'] = new_name

    def resize(self, **kwargs):
        vm_id = ctx.instance.runtime_properties['external_id']
        ins_type = kwargs.get("flavor", "")
        if not ins_type:
            ctx.logger.error("The param `flavor` is required, received param is:{}".format(kwargs))
            return
        params = dict(InstanceId=vm_id, InstanceType=ins_type)
        ret = Helper().execute_request("kec", "modify_instance_type", params)
        ctx.logger.error("resize vm:{}, params:{}, rest: {}".format(vm_id, params, ret))
        self.wait_for_target_state(vm_id, (ksyun_constants.KS_INSTANCE_RESIZE_SUCCESS,
                                           ksyun_constants.KS_INSTANCE_MIGRATE_SUCCESS))
        start_ret = Helper().execute_request('kec', 'start_instances', {"InstanceId.1": vm_id})
        ctx.logger.error("reboot vm:{}, rest: {}".format(vm_id, start_ret))
        self.wait_for_target_state(vm_id, ksyun_constants.KS_INSTANCE_STATE_ACTIVE)
        self.update_runtime_properties(vm_id)
