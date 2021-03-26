# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

KS_INSTANCE_STATE_ACTIVE = 'active'
KS_INSTANCE_STATE_STARTING = 'starting'
KS_INSTANCE_STATE_STOPPED = 'stopped'
KS_INSTANCE_STATE_SCHEDULING = 'scheduling'
KS_INSTANCE_STATE_POWERING_OFF = 'powering-off'
KS_INSTANCE_RESIZE_SUCCESS = 'resize_success_local'
KS_INSTANCE_MIGRATE_SUCCESS = 'migrating_success_off_line'
KS_EIP_TYPE = 'eip_type'
KS_SLB_PUBLIC_TYPE = 'public'
KS_VOLUME_STATE_AVAILABLE = 'available'
KS_VOLUME_STATE_CREATING = 'creating'
KS_VOLUME_STATE_ATTACHING = 'attaching'
KS_VOLUME_STATE_IN_USE = 'in-use'
KS_VOLUME_STATE_DETACHING = 'detaching'
KS_VOLUME_STATE_EXTENDING = 'extending'
KS_VOLUME_STATE_DELETING = 'deleting'
KS_VOLUME_STATE_DELETED = 'deleted'
KS_VOLUME_STATE_RECYCLING = 'recycling'
KS_VOLUME_STATE_ERROR = 'error'
KS_INSTANCE_STATE_CONVERT = {
    'active': 'started',
    'stopped': 'stopped'
}

KS_EIP_STATE_DISASSOCIATE = 'disassociate'
KS_EIP_STATE_ASSOCIATE = 'associate'

KS_SNAPSHOT_STATE_AVAILABLE = ('available', 'ACTIVE')
