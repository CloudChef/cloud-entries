import json
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import httplib2


class Conn_GCP:
    def __init__(self, private_key_id, private_key, client_email, client_id):
        self.KEY_JSON = {
            "type": "service_account",
            "private_key_id": private_key_id,
            "private_key": private_key,
            "client_email": client_email,
            "client_id": client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        self.SCOPE = ['https://www.googleapis.com/auth/compute']
        self.service = None

    def get_service(self, api_name='compute', api_version='v1'):
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(self.KEY_JSON, self.SCOPE)
            http = credentials.authorize(httplib2.Http(disable_ssl_certificate_validation=True))
            service = build(api_name, api_version, http=http)
            return service
        except Exception as e:
            raise Exception("Connect to gcp failed! the error message is {0}".format(e))
