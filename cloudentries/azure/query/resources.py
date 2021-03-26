# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from msrestazure.azure_exceptions import CloudError

from .client import AzureClient


class AzureResource(object):

    def __init__(self, auth_info):
        self.auth_info = auth_info

    def get_mysql_servers(self, params):
        client = AzureClient().create_client('mysql_client', self.auth_info)
        res = []

        for resource_id in params:
            try:
                items = resource_id.split('/')
                subscription_id, resource_group_name, server_name = items[2], items[4], items[8]
                server = client.servers.get(
                    resource_group_name=resource_group_name,
                    server_name=server_name
                )

                server_dict = {
                    'id': server.id,
                    'name': server.name,
                    'sku': server.sku.as_dict()
                }

                res.append(server_dict)
            except CloudError as e:
                if e.status_code != 404:
                    raise

        return res

    def get_sql_databases(self, params):
        client = AzureClient().create_client('sql_client', self.auth_info)
        res = []

        for resource_id in params:
            try:
                items = resource_id.split('/')
                subscription_id, resource_group_name, server_name, db_name = items[2], items[4], items[8], items[10]
                database = client.databases.get(
                    resource_group_name=resource_group_name,
                    server_name=server_name,
                    database_name=db_name
                )
                db_metrics = client.database_usages.list_by_database(
                    resource_group_name=resource_group_name,
                    server_name=server_name,
                    database_name=db_name)

                metrics = [item.as_dict() for item in db_metrics]

                db_dict = {
                    'id': database.id,
                    'status': database.status,
                    'name': database.name,
                    'current_sku': database.current_sku,
                    'metrics': metrics
                }
                res.append(db_dict)
            except CloudError as e:
                if e.status_code != 404:
                    raise
        return res
