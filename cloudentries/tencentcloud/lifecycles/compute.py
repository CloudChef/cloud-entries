# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import uuid

from tencentcloud.cvm.v20170312.models import (
    VirtualPrivateCloud,
    InternetAccessible,
    Placement,
    LoginSettings
)

from abstract_plugin.platforms.common.compute import CommonCompute
from abstract_plugin.platforms.tencentcloud.utils import Base
from abstract_plugin.platforms.tencentcloud.restclient import ComputeHelper, VolumeHelper, NetworkHelper
from abstract_plugin.platforms.common.constants import EXTERNAL_ID
from abstract_plugin.platforms.common.utils import validate_parameter
from cloudify import ctx
from cloudify.utils import decrypt_password
from cloudify.exceptions import NonRecoverableError
from abstract_plugin.platforms.common import constants as common_constants
from . import constants as tc_constants


class Compute(Base, CommonCompute):

    def __init__(self):
        super(Compute, self).__init__()
        self.action_mapper = {
            "create_snapshot": self.create_snapshot,
            "restore_snapshot": self.restore_snapshot,
            "delete_snapshot": self.delete_snapshot,
            "delete_snapshots": self.delete_snapshots,
            "modify_display_name": self.modify_display_name,
            "resize": self.resize,
        }

    def _prepare_virtual_private_cloud_info(self):

        networks = self.get_networks()
        if not networks:
            return
        network = networks[0]
        virtual_private_cloud = VirtualPrivateCloud()
        virtual_private_cloud.VpcId = network.instance.runtime_properties.get('vpc_info').get('VpcId')
        virtual_private_cloud.SubnetId = network.instance.runtime_properties.get('subnet_info').get('SubnetId')
        virtual_private_cloud.PrivateIpAddresses = [self.get_ip(network)]
        return virtual_private_cloud

    def _prepare_internet_accessible(self):
        internet_accessible = InternetAccessible()
        if self.resource_config.get('PublicIpAssigned'):
            internet_accessible.InternetChargeType = self.resource_config.get(
                'InternetChargeType', 'TRAFFIC_POSTPAID_BY_HOUR')
            internet_accessible.InternetMaxBandwidthOut = self.resource_config.get('InternetMaxBandwidthOut', 1)
            internet_accessible.PublicIpAssigned = True
            internet_accessible.BandwidthPackageId = self.resource_config.get('BandwidthPackageId')
        else:
            internet_accessible.InternetMaxBandwidthOut = self.resource_config.get('InternetMaxBandwidthOut', 0)
            internet_accessible.PublicIpAssigned = False
        return internet_accessible

    def _prepare_placement(self):
        placement = Placement()
        placement.Zone = self.resource_config.get('available_zone_id')
        return placement

    def _prepare_login_settings(self):
        login_settings = LoginSettings()
        login_settings.Password = decrypt_password(self.resource_config.get('password'))
        return login_settings

    def get_security_group_id(self):
        sg_rp = self._get_nsg_related_to_compute()
        security_group_id = sg_rp.get('nsg_info', {}).get('SecurityGroupId') if sg_rp else None
        return [security_group_id]

    def _prepare_names(self):
        display_name = self.resource_config.get('instance_name')
        hostname = None
        if not display_name:
            display_name, hostname = self.get_instance_names()
        hostname = self.resource_config.get('hostname') or hostname or display_name
        return (display_name, hostname.replace('_', '-'))

    def _prepare_system_disk(self):
        system_disk_info = {}
        system_disk_info['DiskType'] = self.resource_config.get('system_disk_config').get('volume_type')
        system_disk_info['DiskSize'] = self.resource_config.get('system_disk_config').get('size')
        return system_disk_info

    def _prepare_request_params(self):

        display_name, hostname = self._prepare_names()
        hostname = hostname.strip('-') if ctx.node.properties['os_family'] == 'linux' else hostname[:15].strip('-')
        client_token = ctx.instance.runtime_properties.get('ClientToken', uuid.uuid4().hex)
        request_body = {
            'Placement': self._prepare_placement(),
            'ImageId': self.resource_config.get('image_id'),
            'InstanceChargeType': self.resource_config.get('InstanceChargeType', 'POSTPAID_BY_HOUR'),
            'InstanceType': self.resource_config.get('flavor'),
            'VirtualPrivateCloud': self._prepare_virtual_private_cloud_info(),
            'InternetAccessible': self._prepare_internet_accessible(),
            'InstanceName': display_name,
            'ClientToken': client_token,
            'HostName': hostname,
            'LoginSettings': self._prepare_login_settings(),
            'SystemDisk': self._prepare_system_disk()
        }
        ctx.instance.runtime_properties['ClientToken'] = client_token
        request_body['SecurityGroupIds'] = self.get_security_group_id()
        return request_body

    def _use_external_resource(self, ctx_node_properties):
        if not ctx_node_properties['use_external_resource']:
            ctx.logger.debug('Using Cloudify resource_id: {0}.'.format(ctx_node_properties['resource_id']))
            return False
        else:
            ctx.logger.debug('Using external resource_id: {0}.'.format(ctx_node_properties['resource_id']))
            return True

    def _create_external_instance(self):
        if not self._use_external_resource(ctx.node.properties):
            return
        instance_id = ctx.node.properties['resource_id']
        instance_obj = ComputeHelper().get_instance(instance_id)
        self.update_runtime_properties(instance_obj)
        return True

    def update_runtime_properties(self, instance_obj):
        self.set_base_runtime_props(
            instance_obj['InstanceId'],
            instance_obj['InstanceName']
        )
        self.set_ip_info()
        try:
            ip = instance_obj['PublicIpAddresses'][0]
        except Exception as e:
            ctx.logger.info("Can not get public ip. Try to get private ip. Error message is {0}".format(e))
            ip = instance_obj['PrivateIpAddresses'][0]
        ctx.instance.runtime_properties.update({
            'instance_info': instance_obj,
            'ip': ip,
            'zone_id': instance_obj.get('Placement', {}).get('Zone'),
            'instance_type': instance_obj.get('InstanceType'),
            'instance_charge_type': instance_obj.get('InstanceChargeType'),
            'system_disk_info': instance_obj.get('SystemDisk'),
            'data_disk_info': instance_obj.get('DataDisks'),
            'vpc_id': instance_obj.get('VirtualPrivateCloud', {}).get('VpcId'),
            'subnet_id': instance_obj.get('VirtualPrivateCloud', {}).get('SubnetId'),
            'image_id': instance_obj.get('ImageId'),
            'security_group_ids': instance_obj.get('SecurityGroupIds')
        })

    def create(self, **kwargs):
        ctx.logger.info('Start to create...Resource_config: {}.'.format(self.resource_config))
        if self._create_external_instance():
            return
        request_body = self._prepare_request_params()
        ctx.logger.info('Creating instance of tencent cloud with parameters: {}'.format(request_body))
        instance_info = ComputeHelper().run_instance(request_body)
        self.set_base_runtime_props(
            instance_info['InstanceId'],
            instance_info['InstanceName'],
            request_body['HostName']
        )
        ctx.instance.runtime_properties['zone_id'] = instance_info.get('Placement', {}).get('Zone')
        ctx.instance.runtime_properties['instance_info'] = instance_info
        ctx.logger.info('Created instance successfully.')

        if self.get_eip():
            self.associate_eip()
        self.set_ip_info()
        ctx.instance.update()

    def associate_eip(self):
        eip_instance = self.get_eip()
        vm = ctx.instance
        eip_id = eip_instance.runtime_properties[common_constants.EXTERNAL_ID]
        instance_id = vm.runtime_properties[common_constants.EXTERNAL_ID]
        ctx.logger.info('Start associate EIP:{} to Instance:{}'.format(eip_id, instance_id))
        NetworkHelper().associate_eip(eip_id, instance_id)
        eip_instance.runtime_properties[common_constants.EIP_STATUS] = tc_constants.TENCENT_EIP_STATE_BIND
        eip_instance.runtime_properties[common_constants.EIP_RELATED_INSTANCE_ID] = instance_id
        eip_instance.update()
        ctx.logger.info('Finish associate EIP successfully...')

    def disassociate_eip(self):
        eip_instance = self.get_eip()
        eip_id = eip_instance.runtime_properties[common_constants.EXTERNAL_ID]
        ctx.logger.info('Disassociate EIP id:{}'.format(eip_id))
        NetworkHelper().disassociate_eip(eip_id)
        eip_instance.runtime_properties[common_constants.EIP_STATUS] = tc_constants.TENCENT_EIP_STATE_UNBIND
        eip_instance.runtime_properties.pop(common_constants.EIP_RELATED_INSTANCE_ID)
        ctx.logger.info('Disassociate EIP successfully...')

    def set_ip_info(self):
        instance_id = ctx.instance.runtime_properties[common_constants.EXTERNAL_ID]
        instance_info = ComputeHelper().get_instance(instance_id)
        private_ip = instance_info.get('PrivateIpAddresses')
        subnet_id = instance_info.get('VirtualPrivateCloud').get('SubnetId')
        subnet_info = NetworkHelper().list_subnets(ids=[subnet_id])[0]
        network_info = {
            'name': 'private_ip',
            'cidr': subnet_info.get('CidrBlock'),
            'ip': ','.join(private_ip),
        }
        if not self._use_external_resource(ctx.node.properties):
            # Create by CMP.
            related_network = self.get_primary_network()
            networks_runtime = ctx.instance.runtime_properties.get('networks')
            networks_runtime[related_network.node.id].update(network_info)
            ctx.instance.runtime_properties['networks'].update(networks_runtime)
        else:
            # There is not network connected to instance,instance is external.
            ctx.instance.runtime_properties['networks'] = {
                'Network': network_info,
            }
        if instance_info.get('PublicIpAddresses'):
            public_ip = instance_info.get('PublicIpAddresses')
            public_ip_info = {
                'name': 'public_ip',
                'ip': ','.join(public_ip)
            }
            ctx.instance.runtime_properties['networks'].update({'public_ip': public_ip_info})
            ctx.instance.runtime_properties['ip'] = public_ip[0]
        ips = []
        if instance_info.get('PublicIpAddresses'):
            ips.extend(instance_info.get('PublicIpAddresses'))
        if instance_info.get('PrivateIpAddresses'):
            ips.extend(instance_info.get('PrivateIpAddresses'))
        ctx.instance.runtime_properties['ips'] = ips

    def start(self, **kwargs):
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Starting instance {}.'.format(instance_id))
        ComputeHelper().start_instance(instance_id)
        ctx.logger.info('Instance {} started.'.format(instance_id))
        self.update_networks_info()

    def update_networks_info(self):
        instance_info = ctx.instance.runtime_properties['instance_info']
        networks = ctx.instance.runtime_properties['networks']
        for network, info in list(networks.items()):
            if info.get('subnet_id') == instance_info['VirtualPrivateCloud']['SubnetId']:
                info['ip'] = instance_info['PrivateIpAddresses'][0]
        ctx.instance.runtime_properties['networks'] = networks

    def reboot(self, **kwargs):
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Rebooting instance {}.'.format(instance_id))
        ComputeHelper().reboot_instance(instance_id)
        ctx.logger.info('Instance {} rebooted.'.format(instance_id))

    def stop(self, **kwargs):
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not instance_id:
            return
        if not self.get_vm(instance_id):
            ctx.logger.info('instance {} is not exist, no need to stop'.format(instance_id))
            return
        ctx.logger.info('Stopping instance {}.'.format(instance_id))
        ComputeHelper().stop_instance(instance_id)
        ctx.logger.info('Instance {} stopped.'.format(instance_id))

    def delete(self, **kwargs):
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        snapshot_ids = ctx.instance.runtime_properties.get('snapshot_ids')
        self.delete_snapshots(snapshot_ids)
        if not instance_id:
            return
        if self.get_eip():
            self.disassociate_eip()
        if not self.get_vm(instance_id):
            ctx.logger.info('instance {} is not exist, no need to delete'.format(instance_id))
            return
        ctx.logger.info('Deleting instance {}.'.format(instance_id))
        ComputeHelper().delete_instance(instance_id)
        ctx.instance.runtime_properties = {}
        ctx.instance.update()
        ctx.logger.info('Instance {} deleted.'.format(instance_id))

    def create_snapshot(self, **kwargs):
        ctx.logger.info('Creating snapshot, parameters: {}.'.format(kwargs))
        name = validate_parameter('snapshotName', kwargs)
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        snapshots = VolumeHelper().create_snapshot(name, instance_id)
        existed_snapshots = ctx.instance.runtime_properties.get('snapshot_ids', [])
        ctx.instance.runtime_properties['snapshot_ids'] = existed_snapshots + snapshots
        ctx.logger.info('Snapshot created.')

    def delete_snapshot(self, **kwargs):
        snapshots = validate_parameter('snapshots', kwargs)
        snapshot_ids = [snapshot['snapshotId'] for snapshot in snapshots]
        self.delete_snapshots(snapshot_ids)

    def delete_snapshots(self, snapshot_ids):
        if not snapshot_ids:
            return
        ctx.logger.info('Deleting snapshots: {}.'.format(snapshot_ids))
        VolumeHelper().delete_snapshots(snapshot_ids)
        saved_ids = ctx.instance.runtime_properties['snapshot_ids']
        remained_ids = [saved_id for saved_id in saved_ids if saved_id not in snapshot_ids]
        ctx.instance.runtime_properties['snapshot_ids'] = remained_ids

        ctx.logger.info('Snapshots {} deleted.'.format(snapshot_ids))

    def restore_snapshot(self, **kwargs):
        ctx.logger.info('Applying snapshot, parameters: {}.'.format(kwargs))
        name = validate_parameter('snapshotName', kwargs)
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        VolumeHelper().apply_snapshot(name, instance_id)

    def modify_display_name(self, **kwargs):
        new_name = validate_parameter(ctx.instance.id, kwargs.get('names', {}))
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        ctx.logger.info('Updating name of tencent instance {}.'.format(instance_id))
        ComputeHelper().modify_display_name(instance_id, new_name)
        ctx.instance.runtime_properties['external_name'] = new_name

    def resize(self, **kwargs):
        instance_id = ctx.instance.runtime_properties.get(EXTERNAL_ID)
        if not instance_id:
            ctx.logger.debug('The instance was not created successfully!!!')
            return
        instance_type = validate_parameter('flavor', kwargs)
        ctx.logger.info('Attempt to update instance {0} configuration.'.format(instance_id))
        ComputeHelper().resize(instance_id, instance_type)

    def associate_securitygroup(self, instance_id):
        sg_info = self.get_nsg()
        sg_id = sg_info.get('SecurityGroupId')
        ctx.logger.info('Try to associate instance:{} to security group:{}'.format(instance_id, sg_id))
        try:
            ComputeHelper().associate_securitygroup(instance_id, sg_id)
        except Exception as e:
            raise NonRecoverableError('Associate security group failed,messages:{}'.format(e))
        ctx.instance.runtime_properties['security_group_ids'] = [sg_id]
        ctx.logger.info('Associate instance to security group successfully...')

    def get_vm(self, instance_id):
        return ComputeHelper().get_instance(instance_id)
