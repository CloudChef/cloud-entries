# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import time
import json

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

from tencentcloud.cvm.v20170312 import cvm_client
from tencentcloud.cvm.v20170312.models import (
    RunInstancesRequest,
    DescribeInstancesRequest,
    StartInstancesRequest,
    TerminateInstancesRequest,
    RebootInstancesRequest,
    StopInstancesRequest,
    CreateImageRequest,
    DeleteImagesRequest,
    DescribeImagesRequest,
    ModifyInstancesAttributeRequest,
    ResetInstancesTypeRequest,
    AssociateSecurityGroupsRequest
)

from tencentcloud.vpc.v20170312 import vpc_client
from tencentcloud.vpc.v20170312.models import (
    DescribeVpcsRequest,
    DescribeSubnetsRequest,
    DescribeSecurityGroupsRequest,
    CreateVpcRequest,
    DeleteVpcRequest,
    CreateSubnetRequest,
    DeleteSubnetRequest,
    AllocateAddressesRequest,
    ReleaseAddressesRequest,
    AssociateAddressRequest,
    DisassociateAddressRequest,
    DescribeAddressesRequest,
    CreateSecurityGroupWithPoliciesRequest,
    DeleteSecurityGroupRequest
)
from tencentcloud.cbs.v20170312 import cbs_client
from tencentcloud.cbs.v20170312.models import (
    DescribeDisksRequest,
    CreateDisksRequest,
    TerminateDisksRequest,
    AttachDisksRequest,
    DetachDisksRequest,
    ResizeDiskRequest,
    CreateSnapshotRequest,
    ApplySnapshotRequest,
    DescribeSnapshotsRequest,
    DeleteSnapshotsRequest,
    Filter as Cbs_Filter
)
from qcloud_cos.cos_client import (
    CosS3Client,
    CosConfig)
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import decrypt_password
from abstract_plugin.platforms.tencentcloud import constants
from abstract_plugin.platforms.common.connector import Connector


class Helper(Connector):
    def __init__(self):
        super(Helper, self).__init__()
        self.cred = credential.Credential(
            self.connection_config.get('access_key_id'),
            decrypt_password(self.connection_config.get('access_key_secret')))
        self.region = self.resource_config.get("region")

    def _execute_request(self, func, request_class, **kwargs):
        try:
            req = request_class()
            for key, value in list(kwargs.items()):
                setattr(req, key, value)
            return func(req)
        except TencentCloudSDKException as err:
            if "InvalidPassword" in str(err):
                raise NonRecoverableError('Execute Tencent Cloud request failed: invalid password.')
            raise NonRecoverableError('Execute Tencent Cloud request failed: {}.'.format(err))

    @staticmethod
    def resource_mappers():
        mappers = {
            "Disk": {'Ids': 'DiskIds', 'Set': 'DiskSet'},
            'Instance': {'Ids': 'InstanceIds', 'Set': 'InstanceSet'},
            'Vpc': {'Ids': 'VpcIds', 'Set': 'VpcSet'},
            'Subnet': {'Ids': 'SubnetIds', 'Set': 'SubnetSet'},
            'SecurityGroup': {'Ids': 'SecurityGroupIds', 'Set': 'SecurityGroupSet'},
            'Image': {'Ids': 'ImageIds', 'Set': 'ImageSet'},
            'Snapshot': {'Ids': 'SnapshotIds', 'Set': 'SnapshotSet'},
            'Eip': {'Ids': 'AddressIds', 'Set': 'AddressSet'}
        }
        return mappers

    def is_cloud_disk(self, disk):
        disk_types = ('CLOUD_BASIC', 'CLOUD_SSD', 'CLOUD_PREMIUM')
        return True if disk['DiskType'] in disk_types else False

    def get_instance_disks(self, instance_id, include_system=True):
        self.cvm_client = cvm_client.CvmClient(self.cred, self.region)
        instance = self.list_resources(
            self.cvm_client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])[0]
        system_disk = instance['SystemDisk']
        data_disks = instance.get('DataDisks') or []

        disks = []
        if include_system and self.is_cloud_disk(system_disk):
            disks.append(system_disk)
        for data_disk in data_disks:
            if self.is_cloud_disk(data_disk):
                disks.append(data_disk)
        return disks

    def list_resources(self, func, req_class, resource_type, ids=None, filters=None):
        resource_mapper = self.resource_mappers().get(resource_type)
        ids_key, set_key = resource_mapper.get('Ids'), resource_mapper.get('Set')
        request_body = {ids_key: ids, 'Filters': filters}

        resources = getattr(self._execute_request(func, req_class, **request_body), set_key)
        for i in range(len(resources)):
            resources[i] = json.loads(resources[i].to_json_string())
        return resources

    def wait_for_target_statuses(
            self, resource_type, resource_id, func, req_class, statuses, status_key=None, timeout=600, interval=15):
        ctx.logger.debug(
            'Wait for {} {} status to be {}, timeout is {} seconds.'.format(
                resource_type, resource_id, statuses, timeout))
        remain_times = timeout
        while remain_times:
            time.sleep(interval)
            resources = self.list_resources(func, req_class, resource_type, [resource_id])
            current_status = None
            if resources:
                if not status_key:
                    status_key = resource_type + 'State'
                current_status = resources[0][status_key]
                if current_status in statuses:
                    return resources[0]

            remain_times -= interval

            if resource_type == 'Snapshot' and resources:
                ctx.logger.debug(
                    'Wait for {} {} status to be {}, current status: {}, current percent: {}%.'.format(
                        resource_type, resource_id, statuses, current_status, resources[0]['Percent']))
            else:
                ctx.logger.debug(
                    'Wait for {} {} status to be {}, current status: {}.'.format(
                        resource_type, resource_id, statuses, current_status))
        raise NonRecoverableError('Wait for {} {} to be {} failed after {} seconds.'.format(
            resource_type, resource_id, statuses, timeout))


class NetworkHelper(Helper):
    def __init__(self):
        super(NetworkHelper, self).__init__()
        self.client = vpc_client.VpcClient(self.cred, self.region)

    def list_vpcs(self, ids=None):
        return self.list_resources(self.client.DescribeVpcs, DescribeVpcsRequest, 'Vpc', ids)

    def list_subnets(self, ids=None):
        return self.list_resources(self.client.DescribeSubnets, DescribeSubnetsRequest, 'Subnet', ids)

    def list_securitygroups(self, ids=None):
        return self.list_resources(
            self.client.DescribeSecurityGroups, DescribeSecurityGroupsRequest, 'SecurityGroup', ids)

    def create_securitygroup_with_policies(self, request_body):
        securitygroup_info = json.loads(
            self._execute_request(self.client.CreateSecurityGroupWithPolicies, CreateSecurityGroupWithPoliciesRequest,
                                  **request_body).to_json_string())['SecurityGroup']
        return securitygroup_info

    def delete_securitygroup(self, request_body):
        self._execute_request(self.client.DeleteSecurityGroup, DeleteSecurityGroupRequest, **request_body)

    def create_vpc(self, request_body):
        vpc_info = json.loads(
            self._execute_request(self.client.CreateVpc, CreateVpcRequest, **request_body).to_json_string())['Vpc']

        return vpc_info

    def delete_vpc(self, request_body):
        self._execute_request(self.client.DeleteVpc, DeleteVpcRequest, **request_body)

    def create_subnet(self, request_body):
        subnet_info = json.loads(
            self._execute_request(self.client.CreateSubnet, CreateSubnetRequest, **request_body).to_json_string())[
            'Subnet']

        return subnet_info

    def delete_subnet(self, request_body):
        self._execute_request(self.client.DeleteSubnet, DeleteSubnetRequest, **request_body)

    def allocate_eip(self, **kwargs):
        eip_id = self._execute_request(self.client.AllocateAddresses, AllocateAddressesRequest, **kwargs).AddressSet[0]
        eip_obj = self.wait_for_target_statuses('Eip', eip_id, self.client.DescribeAddresses, DescribeAddressesRequest,
                                                ['UNBIND'], 'AddressStatus')
        return eip_obj

    def associate_eip(self, eip_id, instance_id):
        request_body = {
            'InstanceId': instance_id,
            'AddressId': eip_id,
        }
        self._execute_request(self.client.AssociateAddress, AssociateAddressRequest, **request_body)
        self.wait_for_target_statuses('Eip', eip_id, self.client.DescribeAddresses, DescribeAddressesRequest,
                                      ['BIND'], 'AddressStatus')

    def disassociate_eip(self, eip_id):
        request_body = {
            'AddressId': eip_id
        }
        self._execute_request(self.client.DisassociateAddress, DisassociateAddressRequest, **request_body)
        self.wait_for_target_statuses('Eip', eip_id, self.client.DescribeAddresses, DescribeAddressesRequest,
                                      ['UNBIND'], 'AddressStatus')

    def release_eip(self, eip_id):
        request_body = {
            'AddressIds': [eip_id],
        }
        self._execute_request(self.client.ReleaseAddresses, ReleaseAddressesRequest, **request_body)


class VolumeHelper(Helper):

    def __init__(self):
        super(VolumeHelper, self).__init__()
        self.client = cbs_client.CbsClient(self.cred, self.region)

    def create_snapshot(self, name, instance_id):
        disks = self.get_instance_disks(instance_id)

        snapshot_ids = []

        for disk in disks:
            request_body = {'SnapshotName': name, 'DiskId': disk['DiskId']}
            snapshot_id = self._execute_request(
                self.client.CreateSnapshot, CreateSnapshotRequest, **request_body).SnapshotId
            self.wait_for_target_statuses('Snapshot', snapshot_id, self.client.DescribeSnapshots,
                                          DescribeSnapshotsRequest, ['NORMAL'], timeout=3600)
            snapshot_ids.append(snapshot_id)
        return snapshot_ids

    def delete_snapshots(self, ids):
        request_body = {'SnapshotIds': ids}
        self._execute_request(self.client.DeleteSnapshots, DeleteSnapshotsRequest, **request_body)

    def get_snapshots_and_disks(self, snapshot_name, instance_id):
        disks = self.get_instance_disks(instance_id)
        disk_ids = [disk['DiskId'] for disk in disks]

        filter = Cbs_Filter()
        filter.Name = 'snapshot-name'
        filter.Values = [snapshot_name]
        snapshots = self.list_resources(
            self.client.DescribeSnapshots, DescribeSnapshotsRequest, 'Snapshot', filters=[filter])

        return [snapshot for snapshot in snapshots if snapshot['DiskId'] in disk_ids]

    def apply_snapshot(self, snapshot_name, instance_id):
        snapshots = self.get_snapshots_and_disks(snapshot_name, instance_id)
        for snapshot in snapshots:
            request_body = {'DiskId': snapshot['DiskId'], 'SnapshotId': snapshot['SnapshotId']}
            self._execute_request(self.client.ApplySnapshot, ApplySnapshotRequest, **request_body)
            self.wait_for_target_statuses(
                'Snapshot', snapshot['SnapshotId'], self.client.DescribeSnapshots, DescribeSnapshotsRequest, ['NORMAL'])

    def create_disk(self, request_body):
        disk_id = self._execute_request(self.client.CreateDisks, CreateDisksRequest, **request_body).DiskIdSet[0]
        return self.wait_for_target_statuses(
            'Disk', disk_id, self.client.DescribeDisks, DescribeDisksRequest, ['UNATTACHED', 'ATTACHED'])

    def delete_disks(self, ids=None):
        request_body = {'DiskIds': ids}
        self._execute_request(self.client.TerminateDisks, TerminateDisksRequest, **request_body)

    def attach_disks(self, instance_id, disk_ids, timeout=600, interval=10):
        remain_times = timeout
        error = ""
        while remain_times > 0:
            ctx.logger.info('attach disk:{}'.format(disk_ids))
            try:
                request_body = {'DiskIds': disk_ids, 'InstanceId': instance_id}
                self._execute_request(self.client.AttachDisks, AttachDisksRequest, **request_body)
                self.wait_for_target_statuses(
                    'Disk', disk_ids[0], self.client.DescribeDisks, DescribeDisksRequest, ['ATTACHED'])
            except NonRecoverableError as error:
                ctx.logger.info('waiting for retry attach disk NonRecoverableError: {}'.format(error))
                time.sleep(interval)
                remain_times -= interval
            else:
                return
        raise NonRecoverableError('attach disk failed, {}'.format(error))

    def detach_disks(self, instance_id, disk_ids, timeout=600, interval=10):
        remain_times = timeout
        error = ''
        request_body = {'DiskIds': disk_ids, 'InstanceId': instance_id}
        while remain_times > 0:
            ctx.logger.info('detach disk:{}'.format(disk_ids))
            try:
                self._execute_request(self.client.DetachDisks, DetachDisksRequest, **request_body)
                self.wait_for_target_statuses(
                    'Disk', disk_ids[0], self.client.DescribeDisks, DescribeDisksRequest, ['UNATTACHED'])
            except NonRecoverableError as error:
                ctx.logger.info('waiting for retry detach disk NonRecoverableError: {}'.format(error))
                time.sleep(interval)
                remain_times -= interval
            else:
                return
        raise NonRecoverableError('detach disk failed, {}'.format(error))

    def resize_disk(self, disk_id, size):
        request_body = {'DiskId': disk_id, 'DiskSize': size}
        self._execute_request(self.client.ResizeDisk, ResizeDiskRequest, **request_body)

    def describe_system_disk(self, instance_id):
        request_body = {
            'Filters': [{'Name': 'instance-id', 'Values': [instance_id]},
                        {'Name': 'disk-usage', 'Values': ['SYSTEM_DISK']}]
        }
        return self._execute_request(self.client.DescribeDisks, DescribeDisksRequest, **request_body).DiskSet[0]


class ComputeHelper(Helper):
    def __init__(self):
        super(ComputeHelper, self).__init__()
        self.client = cvm_client.CvmClient(self.cred, self.region)

    def create_image(self, name, instance_id):
        request_body = {'ImageName': name, 'InstanceId': instance_id}
        image_id = self._execute_request(self.client.CreateImage, CreateImageRequest, **request_body).ImageId
        self.wait_for_target_statuses(
            'Instance', instance_id, self.client.DescribeInstances,
            DescribeInstancesRequest, [constants.SUCCESS], status_key='LatestOperationState')
        return self.list_resources(self.client.DescribeImages, DescribeImagesRequest, 'Image', [image_id])[0]

    def delete_image(self, image_ids):
        request_body = {'ImageIds': image_ids}
        self._execute_request(self.client.DeleteImages, DeleteImagesRequest, **request_body)

    def run_instance(self, request_body={}):
        instance_id = self._execute_request(
            self.client.RunInstances, RunInstancesRequest, **request_body).InstanceIdSet[0]
        return self.wait_for_target_statuses('Instance', instance_id, self.client.DescribeInstances,
                                             DescribeInstancesRequest, [constants.RUNNING])

    def start_instance(self, instance_id):
        instance = self.list_resources(
            self.client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])[0]
        if instance['InstanceState'] == constants.RUNNING:
            return

        if ctx.workflow_id not in ('install', 'heal'):
            request_body = {'InstanceIds': [instance_id]}
            self._execute_request(self.client.StartInstances, StartInstancesRequest, **request_body)
        self.wait_for_target_statuses(
            'Instance', instance_id, self.client.DescribeInstances, DescribeInstancesRequest, [constants.RUNNING])

    def stop_instance(self, instance_id):
        request_body = {'InstanceIds': [instance_id]}
        instance = self.list_resources(
            self.client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])[0]
        if instance['InstanceState'] == constants.STOPPED:
            return

        self._execute_request(self.client.StopInstances, StopInstancesRequest, **request_body)
        self.wait_for_target_statuses(
            'Instance', instance_id, self.client.DescribeInstances, DescribeInstancesRequest, [constants.STOPPED])

    def delete_instance(self, instance_id):
        request_body = {'InstanceIds': [instance_id]}
        disks = self.get_instance_disks(instance_id, include_system=False)
        disk_ids = [disk['DiskId'] for disk in disks]
        self._execute_request(self.client.TerminateInstances, TerminateInstancesRequest, **request_body)
        instances = self.list_resources(
            self.client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])
        while instances:
            instances = self.list_resources(
                self.client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])
            time.sleep(1)
        if disk_ids:
            VolumeHelper().delete_disks(disk_ids)

    def reboot_instance(self, instance_id):
        request_body = {'InstanceIds': [instance_id]}
        self._execute_request(self.client.RebootInstances, RebootInstancesRequest, **request_body)
        self.wait_for_target_statuses(
            'Instance', instance_id, self.client.DescribeInstances, DescribeInstancesRequest, [constants.RUNNING])

    def get_instance(self, instance_id):
        instances = self.list_resources(
            self.client.DescribeInstances, DescribeInstancesRequest, 'Instance', ids=[instance_id])
        if instances is None:
            raise NonRecoverableError(
                'Cannot use_external_resource because instance_id {0} is not in this account.'.format(instance_id))
        else:
            return instances[0]

    def modify_display_name(self, instance_id, name):
        request_body = {'InstanceIds': [instance_id], 'InstanceName': name}
        self._execute_request(self.client.ModifyInstancesAttribute, ModifyInstancesAttributeRequest, **request_body)

    def resize(self, instance_id, instance_type):
        request_body = {'InstanceIds': [instance_id], 'InstanceType': instance_type}
        self._execute_request(self.client.ResetInstancesType, ResetInstancesTypeRequest, **request_body)
        self.wait_for_target_statuses('Instance', instance_id, self.client.DescribeInstances, DescribeInstancesRequest,
                                      [constants.SUCCESS], 'LatestOperationState')

    def associate_securitygroup(self, instance_id, sg_id):
        request_body = {
            'SecurityGroupIds': [sg_id],
            'InstanceIds': [instance_id]
        }
        self._execute_request(self.client.AssociateSecurityGroups, AssociateSecurityGroupsRequest, **request_body)


class OssHelper(Helper):
    def __init__(self):
        super(OssHelper, self).__init__()
        self.conf = CosConfig(SecretId=getattr(self.cred, 'secretId'), SecretKey=getattr(self.cred, 'secretKey'),
                              Region=self.region)
        self.client = CosS3Client(self.conf)

    def create_bucket(self, request_body):
        self.client.create_bucket(
            Bucket=request_body.get('Bucket')
        )

    def delete_bucket(self, request_body):
        self.client.delete_bucket(
            Bucket=request_body.get('Bucket'))
