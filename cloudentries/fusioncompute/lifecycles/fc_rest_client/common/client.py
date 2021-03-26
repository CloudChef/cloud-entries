# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import os
import json
import logging
import requests
from .. import exceptions


class RestClient(object):
    def __init__(self,
                 auth=None,
                 verify=False,
                 cert=None):
        self.auth = auth
        self.verify = verify
        self.cert = cert
        self.logger = logging.getLogger('fc_rest_client.http')

    @property
    def url(self):
        return self.auth.base_url

    @property
    def headers(self):
        return self.auth.get_auth_headers()

    def _raise_client_error(self, response, url=None):
        try:
            result = response.json()
        except Exception:
            if response.status_code == 304:
                error_msg = 'Nothing to modify'
                self._prepare_and_raise_exception(
                    message=error_msg,
                    error_code='not_modified',
                    status_code=response.status_code,
                    server_traceback='')
            else:
                message = response.content
                if url:
                    message = '{0} [{1}]'.format(message, url)
                error_msg = '{0}: {1}'.format(response.status_code, message)
            raise exceptions.FusionComputeClientError(
                error_msg,
                status_code=response.status_code)
        message = result.get('message') or response.content
        code = result.get('error_code')
        server_traceback = result.get('server_traceback')
        self._prepare_and_raise_exception(
            message=message,
            error_code=code,
            status_code=response.status_code,
            server_traceback=server_traceback)

    @staticmethod
    def _prepare_and_raise_exception(message,
                                     error_code,
                                     status_code,
                                     server_traceback=None):

        error = exceptions.ERROR_MAPPING.get(error_code,
                                             exceptions.FusionComputeClientError)
        raise error(message, server_traceback,
                    status_code, error_code=error_code)

    def verify_response_status(self, response, expected_code=200):
        if response.status_code != expected_code:
            self._raise_client_error(response)

    def _do_request(self, requests_method, request_url, body, params, headers,
                    expected_status_code, stream, verify, timeout):
        response = requests_method(request_url,
                                   data=body,
                                   params=params,
                                   headers=headers,
                                   stream=stream,
                                   verify=verify,
                                   timeout=timeout)
        if self.logger.isEnabledFor(logging.DEBUG):
            for hdr, hdr_content in list(response.request.headers.items()):
                self.logger.debug('request header:  %s: %s'
                                  % (hdr, hdr_content))
            self.logger.debug('reply:  "%s %s" %s'
                              % (response.status_code,
                                 response.reason, response.content))
            for hdr, hdr_content in list(response.headers.items()):
                self.logger.debug('response header:  %s: %s'
                                  % (hdr, hdr_content))

        if response.status_code != expected_status_code:
            self._raise_client_error(response, request_url)

        if stream:
            return StreamedResponse(response)

        response_json = response.json()

        if response.history:
            response_json['history'] = response.history

        return response_json

    def get_request_verify(self):
        if self.cert:
            # verify will hold the path to the self-signed certificate
            return self.cert
        return self.verify

    def do_request(self,
                   requests_method,
                   uri,
                   data=None,
                   params=None,
                   headers=None,
                   expected_status_code=200,
                   stream=False,
                   timeout=None):
        request_url = self.url + uri

        # build headers
        headers = headers or {}
        total_headers = self.headers.copy()
        total_headers.update(headers)

        params = params or {}

        # data is either dict, bytes data or None
        is_dict_data = isinstance(data, dict)
        body = json.dumps(data) if is_dict_data else data
        if self.logger.isEnabledFor(logging.DEBUG):
            log_message = 'Sending request: {0} {1}'.format(
                requests_method.__name__.upper(),
                request_url)
            if is_dict_data:
                log_message += '; body: {0}'.format(body)
            elif data is not None:
                log_message += '; body: bytes data'
            self.logger.debug(log_message)
        return self._do_request(
            requests_method=requests_method, request_url=request_url,
            body=body, params=params, headers=total_headers,
            expected_status_code=expected_status_code, stream=stream,
            verify=self.get_request_verify(), timeout=timeout)

    def get(self, uri, data=None, params=None, headers=None,
            expected_status_code=200, stream=False, timeout=None):
        return self.do_request(requests.get,
                               uri,
                               data=data,
                               params=params,
                               headers=headers,
                               expected_status_code=expected_status_code,
                               stream=stream,
                               timeout=timeout)

    def put(self, uri, data=None, params=None, headers=None,
            expected_status_code=200, stream=False, timeout=None):
        return self.do_request(requests.put,
                               uri,
                               data=data,
                               params=params,
                               headers=headers,
                               expected_status_code=expected_status_code,
                               stream=stream,
                               timeout=timeout)

    def patch(self, uri, data=None, params=None, headers=None,
              expected_status_code=200, stream=False, timeout=None):
        return self.do_request(requests.patch,
                               uri,
                               data=data,
                               params=params,
                               headers=headers,
                               expected_status_code=expected_status_code,
                               stream=stream,
                               timeout=timeout)

    def post(self, uri, data=None, params=None, headers=None,
             expected_status_code=200, stream=False, timeout=None):
        return self.do_request(requests.post,
                               uri,
                               data=data,
                               params=params,
                               headers=headers,
                               expected_status_code=expected_status_code,
                               stream=stream,
                               timeout=timeout)

    def delete(self, uri, data=None, params=None, headers=None,
               expected_status_code=200, stream=False, timeout=None):
        return self.do_request(requests.delete,
                               uri,
                               data=data,
                               params=params,
                               headers=headers,
                               expected_status_code=expected_status_code,
                               stream=stream,
                               timeout=timeout)


class StreamedResponse(object):

    def __init__(self, response):
        self._response = response

    @property
    def headers(self):
        return self._response.headers

    def bytes_stream(self, chunk_size=8192):
        return self._response.iter_content(chunk_size)

    def lines_stream(self):
        return self._response.iter_lines()

    def close(self):
        self._response.close()


class FusionComputeBase(object):
    BASE_URI = os.environ.get("FUSION_COMPUTE_BASE_URL") or "/service"
    # IDENTIFIER should be overwrited by subclass
    IDENTIFIER = ""

    def __init__(self, rest_client):
        self.rest_client = rest_client

    def urn2uri(self, urn):
        return urn.replace(":", "/").replace("urn", self.BASE_URI)

    def list(self, urn):
        """
        ClustersClient,HostsClient,ServersClient,DvSwitchsClient,DatastoresClient --> site_urn
        PortGroupsClient --> dvswitch_urn
        SitesClient --> overwrited. no parameter.

        Example:
            list sites --> SitesClient().list()
            list clusters --> ClustersClient().list("urn:sites:48630826")
        """
        uri = '/'.join([self.urn2uri(urn), self.IDENTIFIER])
        return self.rest_client.get(uri)

    def get(self, urn):
        uri = self.urn2uri(urn)
        return self.rest_client.get(uri)
