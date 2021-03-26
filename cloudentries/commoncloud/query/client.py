# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

class BasicConnection(object):
    """
    Connect to cloud platform
    """
    pass


class BasicClient(object):
    """
    Send request to cloud platform's each API
    """

    def __init__(self):
        self.conn = BasicConnection()
