# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from . import constants

# fabric
from fabric import api as fabric_api
from fabric.context_managers import settings, hide

# winrm
from cloudchef_integration.tasks.cloud_resources.hyper_v.client import SessionUTF8

# ipmi
import pyipmi.interfaces


# Linux
class FabricRunner(object):
    def __init__(self, host, port, username, password, key=None):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.key = key

    def set_env(self):
        env = {
            "host_string": self.host,
            "port": self.port,
            "user": self.username,
            "password": self.password,
            "key": self.key
        }
        return env

    def run(self, script):
        try:
            with settings(**self.set_env()):
                with hide('warnings'):
                    res = fabric_api.sudo(script, quiet=True)
            if res.return_code not in (constants.SHELL_SUCCESS_EXIT_CODE, constants.SHELL_REBOOT_SUCCESS_EXIST_CODE):
                raise Exception("fabric exec {0} failed, the error message is {1}".format(script, str(res)))
            else:
                return str(res)
        except Exception as e:
            raise Exception("fabric runner is failed, the error message is {0}".format(e))


class LinuxClient(FabricRunner):
    def start(self):
        pass

    def stop(self):
        self.run(constants.LINUX_CMD_STOP)

    def reboot(self):
        self.run(constants.LINUX_CMD_REBOOT)

    def validate(self):
        self.run(constants.LINUX_CMD_VALIDATE)
        return {'state': 'Running'}


# Windows
class WinRMClient(object):
    def __init__(self, host, port, username, password):
        self.url = "{host}:{port}".format(host=host, port=port)
        self.username = username
        self.password = password

    def run(self, script):
        try:
            client = SessionUTF8(self.url, auth=(self.username, self.password), transport='ntlm')
            r = client.run_ps(script)
            if r.status_code != 0:
                raise Exception("Execute script failed! script is : {0}, the status code is {1}"
                                "the standard output is {2}, the standard error is: {3}".format(
                                    script, r.status_code, r.std_out.decode('utf-8'), r.std_err))
            return r.std_out.decode('utf-8')
        except Exception as e:
            raise Exception("Execute script failed! script is : {0}, the error message is: {1}".format(
                script, e))


class WindowsClient(WinRMClient):
    def start(self):
        pass

    def stop(self):
        self.run(constants.WINDOWS_CMD_STOP)

    def reboot(self):
        self.run(constants.WINDOWS_CMD_REBOOT)

    def validate(self):
        self.run(constants.WINDOWS_CMD_VALIDATE)
        return {'state': 'Running'}


# physical machine
class IPMIClient(object):
    def __init__(self, host, username, password, port=623, local_address=0x20):
        self.host = host
        self.username = username
        self.password = password
        self.port = int(port)
        self.local_address = int(str(local_address), 0)

    def get_client(self):
        interface = pyipmi.interfaces.create_interface(interface=constants.IPMI_INTERFACE_RMCP)
        ipmi = pyipmi.create_connection(interface)
        ipmi.session.set_session_type_rmcp(host=self.host, port=self.port)
        ipmi.session.set_auth_type_user(username=self.username, password=self.password)
        ipmi.target = pyipmi.Target(ipmb_address=self.local_address)
        ipmi.session.establish()
        return ipmi

    def run(self, action):
        try:
            ipmi = self.get_client()
            res = getattr(ipmi, action)()
            ipmi.session.close()
        except Exception as e:
            raise Exception("Do action {0} failed! the error message is {1}".format(action, e))
        return res


class PhysicalMachineClient(IPMIClient):
    def get_status(self):
        """
        :return: example
        {
            'control_fault': False,
            'fault': False,
            'interlock': False,
            'overload': False,
            'power_on': True,
            'restore_policy': 1
        }
        """
        res = self.run(constants.IPMI_ACTION_GET_STATUS)
        return res.__dict__

    def start(self):
        self.run(constants.IPMI_ACTION_START)

    def stop(self):
        self.run(constants.IPMI_ACTION_STOP)

    def reboot(self):
        self.run(constants.IPMI_ACTION_REBOOT)

    def validate(self):
        ipmi_info = self.get_status()
        return {
            'state': 'Running' if ipmi_info.get('power_on') is True else 'Stopped',
            'additional_information': ipmi_info
        }
