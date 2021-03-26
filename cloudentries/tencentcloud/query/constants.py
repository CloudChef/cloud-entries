# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

INSTANCE_STATUSES = {
    "LAUNCHING": "starting,POWERED_ON",
    "RUNNING": "started,POWERED_ON",
    "RESTARTING": "starting,POWERED_ON",
    "REBOOTING": "starting,POWERED_ON",
    "SHUTTINGDOWN": "stopping,POWERED_ON",
    "SHUTDOWN": "stopped,POWERED_OFF",
    "TERMINATING": "deleting,POWERED_OFF",
    "TERMINATED": "lost,UNKNOWN",
    "PENDING": "starting,POWERED_ON",
    "STOPPED": "stopped,POWERED_OFF"
}

INSTANCE_TYPE = {'标准型': ['S1', 'S2', 'S2ne', 'SA1', 'S3', 'SN3ne', 'S4', 'SA2', 'S5'],
                 '内存型': ['M1', 'M2', 'M3', 'M4', 'M5'],
                 '高IO型': ['IT3'],
                 '大数据型': ['D2'],
                 '计算型': ['CN3', 'C3', 'C2'],
                 '批量型': ['BC1', 'BS1'],
                 '黑石物理服务器2.0': ['BMS4', 'BMD2']}
