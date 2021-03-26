# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from cloudify.exceptions import NonRecoverableError
from .utils import validate_parameter


class CommonResource(object):
    def create(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    @staticmethod
    def _custom_operation(action_mapper, **kwargs):
        action = validate_parameter('action', kwargs)
        if action in action_mapper:
            action_mapper[action](**kwargs)
        else:
            raise NonRecoverableError("Operation '{0}' is not supported yet.".format(action))

    def custom_operation(self, **kwargs):
        action_mapper = self.action_mapper if hasattr(self, 'action_mapper') else {}
        self._custom_operation(action_mapper, **kwargs)
