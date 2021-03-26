# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from abstract_plugin.platforms.common.network import CommonNetwork
from abstract_plugin.platforms.tencentcloud.restclient import NetworkHelper
from abstract_plugin.platforms.tencentcloud.utils import Base
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
import time


class Network(CommonNetwork, Base):

    def __init__(self):
        super(Network, self).__init__()

    def create(self, **kwargs):
        vpc_id = validate_parameter('resource_id', self.resource_config)
        try:
            vpc_info = NetworkHelper().list_vpcs(ids=[vpc_id])[0]
        except Exception as e:
            raise NonRecoverableError("Vpc {} not exists.Error Message:{}".format(vpc_id, e))
        if self.use_external_resource:
            subnet_id = validate_parameter('subnet_id', self.resource_config)
            try:
                subnet_info = NetworkHelper().list_subnets(ids=[subnet_id])[0]
                ctx.logger.debug("Use existed tencentcloud network: {}, subnet: {}.".format(vpc_id, subnet_id))
                self.set_base_runtime_props(resource_id=subnet_info['SubnetId'], name=subnet_info['SubnetName'])
                ctx.instance.runtime_properties['vpc_info'] = vpc_info
                ctx.instance.runtime_properties['subnet_info'] = subnet_info
            except Exception as e:
                raise NonRecoverableError("Create network failed: {}.".format(e))
        else:
            ctx.logger.info('Start to create subnet...')
            subnet_name = validate_parameter('subnet_name', self.resource_config)
            cidr_block = validate_parameter('cidr_block', self.resource_config)
            zone = validate_parameter('available_zone_id', self.resource_config)
            request_body = {
                'SubnetName': subnet_name,
                'CidrBlock': cidr_block,
                'Zone': zone,
                'VpcId': vpc_id
            }
            ctx.logger.info('Try to Create subnet with parameters:{}'.format(request_body))
            try:
                subnet_info = NetworkHelper().create_subnet(request_body)
            except Exception as e:
                raise NonRecoverableError("Create network failed...messages: {}.".format(e))
            self.set_base_runtime_props(resource_id=subnet_info['SubnetId'], name=subnet_info['SubnetName'])
            ctx.instance.runtime_properties['vpc_info'] = vpc_info
            ctx.instance.runtime_properties['subnet_info'] = subnet_info
            ctx.logger.info('Created subnet successfully...vpc:{},subnet:{}'.format(vpc_id, subnet_info['SubnetId']))

    def delete(self, **kwargs):
        ctx.logger.info('Start to delete subnet...')
        ret_msg = "Delete subnet successfully..."
        if not self.use_external_resource:
            subnet_id = ctx.instance.runtime_properties['subnet_info']['SubnetId']
            request_body = {
                'SubnetId': subnet_id
            }
            ctx.logger.info('Try to delete subnet with parameters:{}'.format(request_body))
            timeout = time.time() + 600  # default timeout:10min
            while time.time() < timeout:
                try:
                    NetworkHelper().delete_subnet(request_body)
                except Exception as e:
                    ret_msg = str(e)
                    if "ResourceInUse" in ret_msg:
                        time.sleep(10)
                        continue
                    else:
                        ret_msg = 'Delete subnet:{} failed,Error Message:{}'.format(subnet_id, e)
                clear_runtime_properties()
                ctx.logger.info(ret_msg)
                break
            else:
                clear_runtime_properties()
                ctx.logger.info('Delete subnet:{} failed,Error Message:{}'.format(subnet_id, ret_msg))
        else:
            clear_runtime_properties()
            ctx.logger.info(ret_msg)
