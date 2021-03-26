from cloudchef_integration.tasks.cloud_resources.commoncloud.utils import BasicSchema, ParamType


class ImageDesc(object):
    Schema = {
        "platform": BasicSchema.schema(raw_key="osType", required=False, param_type=ParamType.String)
    }


class SubnetDesc(object):
    Schema = {
        "l2NetworkUuid": BasicSchema.schema(raw_key="NetworkId", required=False, param_type=ParamType.String)
    }
