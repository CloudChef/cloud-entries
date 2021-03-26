from abstract_plugin.platforms.common.oss import CommonOss
from abstract_plugin.platforms.tencentcloud.utils import Base
from abstract_plugin.platforms.tencentcloud.restclient import OssHelper
from abstract_plugin.platforms.common.utils import validate_parameter, clear_runtime_properties
from cloudify.exceptions import NonRecoverableError
from cloudify import ctx
from abstract_plugin.platforms.common import constants


class Oss(CommonOss, Base):
    def create(self):
        bucket_name = validate_parameter('bucket_name', self.resource_config)
        app_id = validate_parameter('app_id', self.connection_config)
        bucket_name = '-'.join([bucket_name, app_id])
        if not self.use_external_resource:
            request_body = {
                'Bucket': bucket_name
            }
            try:
                OssHelper().create_bucket(request_body)
            except Exception as e:
                raise NonRecoverableError('Create bucket failed...Messages:{}'.format(e))
            self.set_base_runtime_props(resource_id=bucket_name, name=bucket_name)
        else:
            ctx.logger.info('Use external resource...Bucket name:{}'.format(bucket_name))

    def delete(self):
        if not self.use_external_resource:
            bucket_name = ctx.instance.runtime_properties[constants.EXTERNAL_ID]
            request_body = {
                'Bucket': bucket_name
            }
            try:
                OssHelper().delete_bucket(request_body)
            except Exception as e:
                ctx.logger.info('Delete bucket failed...Messages:{}'.format(e))
        clear_runtime_properties()
