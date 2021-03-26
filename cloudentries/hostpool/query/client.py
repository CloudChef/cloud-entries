# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudchef_integration.tasks.cloud_resources.hostpool.utils import LinuxClient, WindowsClient, PhysicalMachineClient
from . import constants


class HostClient(object):
    def __init__(self, config, params):
        """
        :param config:
          {
            'ip': ip, required
            'hostname': hostname,
            'ipmi_enabled': true for physical_machine, false for virtual_machine
            'os_family': linux or windows required
            'protocol': SSH or WinRM or IPMI, required
            'port': port. SSH, default 22; WinRM, default 5985. required
            'user': user,
            'password': password,
            'key_pair': key,
            'ipmi_ip': host ip, when ipmi_enabled is true, required
            'ipmi_user': username, when ipmi_enabled is true, required
            'ipmi_password': password, when ipmi_enabled is true, required
            'ipmi_port': port, default 623, when ipmi_enabled is true, required
            'ipmi_local_address': default 0x20, when ipmi_enabled is true, required
          }
        """
        self.resource_config = params
        self.os_family = self.get_valid_parameter('os_family', self.resource_config)
        self.ipmi_enabled = self.get_valid_parameter('ipmi_enabled', self.resource_config)
        self.client = self.get_client()

    @staticmethod
    def get_valid_parameter(param, param_dict):
        if not param_dict:
            param_dict = {}
        param_value = param_dict.get(param)
        if param_value is None:
            raise Exception(
                "Invalid args: {0}, required parameter {1} is not provided.".format(param_dict, param))
        return param_value

    def get_client(self):
        if str(self.ipmi_enabled).lower() == 'true':
            return PhysicalMachineClient(
                host=self.get_valid_parameter('ipmi_ip', self.resource_config),
                username=self.get_valid_parameter('ipmi_user', self.resource_config),
                password=self.get_valid_parameter('ipmi_password', self.resource_config),
                port=self.resource_config.get('ipmi_port') or constants.IPMI_DEFAULT_PORT,
                local_address=self.resource_config.get('ipmi_local_address') or constants.IPMI_DEFAULT_LOCAL_ADDRESS
            )
        elif self.os_family == 'windows':
            return WindowsClient(
                host=self.get_valid_parameter('ip', self.resource_config),
                port=self.resource_config.get('port') or constants.WINRM_DEFAULT_PORT,
                username=self.get_valid_parameter('user', self.resource_config),
                password=self.get_valid_parameter('password', self.resource_config)
            )
        else:
            return LinuxClient(
                host=self.get_valid_parameter('ip', self.resource_config),
                port=self.resource_config.get('port') or constants.SSH_DEFAULT_PORT,
                username=self.get_valid_parameter('user', self.resource_config),
                password=self.resource_config.get('password'),
                key=self.resource_config.get('key_pair'),
            )

    def do_action(self, action):
        try:
            res = getattr(self.client, action)()
            return res
        except Exception as e:
            raise Exception("Do action {0} failed! the error message is {1}".format(action, e))

    @property
    def instance(self):
        try:
            res = self.client.validate()
            return [res]
        except Exception:
            return [{'state': 'Lost'}]
