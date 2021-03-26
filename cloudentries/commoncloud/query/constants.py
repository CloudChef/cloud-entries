# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

SUCCESS_CODE = [200]

InstanceStatusMapper = {
    "configured": ["configured"],
    "configuring": ["configuring"],
    "creating": ["scheduling", "provisioning", "creating"],
    "deleted": ["deleted"],
    "deleting": ["recycling", "shutting-down", "terminating"],
    "install fail": ["install fail"],
    "lost": ["unknown", "undefined", "terminated"],
    "purged": ["purged"],
    "started": ["active", "running", "start"],
    "starting": ["rebuilding", "starting", "rebooting", "launching", "restarting", "staging", "initializing"],
    "stopped": ["stopped", "suspended", "terminated", "repairing", "stop", "unavailable"],
    "stopping": ["stopping", "stop", "pause", "hibernating", "suspending"],
    "uninitialized": ["uninitialized"]
}


PowerStatusMapper = {
    "POWERED_OFF": ["stopped", "shutdown", "terminating"],
    "POWERED_ON": ["running", "rebuilding", "launching", "restarting", "rebooting", "shuttingdown", "pending"],
    "SUSPENDED": ["suspended"],
    "UNKNOWN": ["unknown", "undefined", "terminated"]
}
