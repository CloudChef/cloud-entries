# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from msrestazure.azure_cloud import AZURE_CHINA_CLOUD
from msrest.exceptions import AuthenticationError
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.rdbms.mysql import MySQLManagementClient
from azure.mgmt.sql import SqlManagementClient


class AzureClient(object):

    def __init__(self):
        self.clients = {
            'mysql_client': MySQLManagementClient,
            'sql_client': SqlManagementClient
        }

    def get_credentials(self, auth_params):
        credentials = ServicePrincipalCredentials(
            client_id=auth_params['client_id'],
            secret=auth_params['key'],
            tenant=auth_params['tenant'],
            cloud_environment=AZURE_CHINA_CLOUD,
            timeout=2
        )
        return credentials

    def create_client(self, client_name, auth_params):

        try:

            subscription_id = auth_params['subscription_id']
            credentials = self.get_credentials(auth_params)
            client = self.clients[client_name](
                credentials, subscription_id,
                base_url=AZURE_CHINA_CLOUD.endpoints.resource_manager)
            return client
        except AuthenticationError as e:
            raise
        except Exception as e:
            raise
