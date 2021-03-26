# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

class BasicResource(object):
    """
    Recv API request from CMP
    """

    def __init__(self, connect_params, query_params=None):
        """
        the name of `connect_params` & `query_params` cannot change
        """
        self.connect_params = connect_params
        self.query_params = query_params
