# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

class ValidationError(Exception):
    """The validation exception"""

    message = "ValidationError"

    def __init__(self, message=None):
        self.message = message or self.message
        super(ValidationError, self).__init__(self.message)


class FusionComputeClientError(Exception):

    def __init__(self, message, server_traceback=None,
                 status_code=-1, error_code=None):
        super(FusionComputeClientError, self).__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.server_traceback = server_traceback

    def __str__(self):
        if self.status_code != -1:
            return '{0}: {1}'.format(self.status_code, self.message)
        return self.message


class IllegalParametersError(FusionComputeClientError):
    ERROR_CODE = 'illegal_parameters_error'


class ServerNotFound(FusionComputeClientError):
    ERROR_CODE = 'server_not_found'


class ServerCreationFailed(FusionComputeClientError):
    ERROR_CODE = 'server_creation_failed'


ERROR_MAPPING = dict([
    (error.ERROR_CODE, error)
    for error in [
        IllegalParametersError,
        ServerNotFound,
        ServerCreationFailed
    ]])
