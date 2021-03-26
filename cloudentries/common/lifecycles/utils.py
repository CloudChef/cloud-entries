# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import socket
import struct

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from . import constants


def get_instance_or_source_node_properties():
    if ctx.type == constants.RELATIONSHIP_INSTANCE:
        return ctx.source.node.properties
    elif ctx.type == constants.NODE_INSTANCE:
        return ctx.node.properties
    else:
        raise NonRecoverableError(
            'Invalid use of ctx. '
            'get_instance_or_source_node_properties '
            'called in a context that is not {0} or {1}.'.format(constants.RELATIONSHIP_INSTANCE,
                                                                 constants.NODE_INSTANCE))


def get_connection_config():
    if ctx.type == constants.RELATIONSHIP_INSTANCE:
        return ctx.source.node.connection_config
    elif ctx.type == constants.NODE_INSTANCE:
        return ctx.node.connection_config
    else:
        raise NonRecoverableError(
            'Invalid use of ctx. '
            'get_connection_config '
            'called in a context that is not {0} or {1}.'.format(constants.RELATIONSHIP_INSTANCE,
                                                                 constants.NODE_INSTANCE))


def get_ctx_instance():
    ctx_instance = ctx.instance if ctx.type == constants.NODE_INSTANCE else ctx.source.instance
    return ctx_instance


def get_node_resource_config(node):
    return node.properties.get('resource_config', {})


def get_node_resource_bundle_config(node):
    return get_node_resource_config(node).get('resource_bundle_config', {})


def get_cloud_entry_type():
    connection_config = get_connection_config()
    return validate_parameter('cloud_entry_type', connection_config)


def validate_parameter(param, param_dict, not_empty=False):
    param_value = param_dict.get(param)
    if param_value is None or (not param_value and not_empty):
        raise NonRecoverableError(
            "Invalid args: {0}, required parameter {1} is not provided.".format(param_dict, param))
    return param_value


def drop_none(params):
    return dict((k, v) for k, v in list(params.items()) if v)


def cidr_to_netmask(cidr):
    network, net_bits = cidr.split('/')
    host_bits = 32 - int(net_bits)
    netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
    mask_network = []
    for i in range(4):
        mask_network.append(int(network.split('.')[i]) & int(netmask.split('.')[i]))
    network = '.'.join([str(i) for i in mask_network])

    return network, netmask


def is_heal_and_use_external():
    resource_config = ctx.node.properties.get('resource_config')
    if ctx.workflow_id == 'heal' and resource_config.get('use_external_resource'):
        return True


def set_runtime_properties(key, value, ctx_instance=None):
    if not ctx_instance:
        ctx_instance = get_ctx_instance()
    ctx_instance.runtime_properties[key] = value


def clear_runtime_properties():
    rt_properties = ctx.instance.runtime_properties
    if ctx.workflow_id == 'heal' and ctx.node.type == constants.COMPUTE_NODE_TYPE:
        ip_pool_info = rt_properties.get('ip_pool_info', {})
        networks = rt_properties.get('networks')
        dns_servers, routes = rt_properties.get('dns_servers'), rt_properties.get('routes')
        ctx.instance.runtime_properties = {
            constants.EXTERNAL_NAME: rt_properties.get(constants.EXTERNAL_NAME),
            constants.EXTERNAL_HOSTNAME: rt_properties.get(constants.EXTERNAL_HOSTNAME),
            'ip_pool_info': ip_pool_info,
            'networks': networks,
            'dns_servers': dns_servers,
            'routes': routes
        }
    else:
        ctx.instance.runtime_properties = {}


# transfer vm status to standard format
def format_ins_status(raw_status, default_status="unknown"):
    for status, raw_lst in list(constants.InstanceStatusMapper.items()):
        if raw_status.lower() in raw_lst:
            return status
    return default_status


# transfer vm power status to standard format
def format_power_status(raw_status, default_status="SUSPENDED"):
    for status, raw_lst in list(constants.PowerStatusMapper.items()):
        if raw_status.lower() in raw_lst:
            return status
    return default_status
