# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

# linux
LINUX_CMD_STOP = 'shutdown -h now'
LINUX_CMD_REBOOT = 'shutdown -r now'
LINUX_CMD_VALIDATE = 'echo'
SSH_DEFAULT_PORT = 22
SHELL_SUCCESS_EXIT_CODE = 0
SHELL_REBOOT_SUCCESS_EXIST_CODE = -1

# windows
WINDOWS_CMD_STOP = 'shutdown -s -t 0 -f'
WINDOWS_CMD_REBOOT = 'shutdown -r -t 0 -f'
WINDOWS_CMD_VALIDATE = 'cls'
WINRM_DEFAULT_PORT = 5895

# ipmi
IPMI_INTERFACE_RMCP = 'rmcp'
IPMI_ACTION_GET_STATUS = 'get_chassis_status'
IPMI_ACTION_START = 'chassis_control_power_up'
IPMI_ACTION_STOP = 'chassis_control_power_down'
IPMI_ACTION_REBOOT = 'chassis_control_hard_reset'
IPMI_DEFAULT_PORT = 623
IPMI_DEFAULT_LOCAL_ADDRESS = 0x20
