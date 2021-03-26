# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from abstract_plugin.platforms.common.connector import Connector


class Base(Connector):
    def __init__(self):
        super(Base, self).__init__()
