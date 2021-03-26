# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from kscore.exceptions import ClientError
from cloudify.exceptions import NonRecoverableError
from functools import wraps


def client_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kw):

        try:
            return func(*args, **kw)
        except ClientError as e:
            raise NonRecoverableError(e)
    return wrapper
