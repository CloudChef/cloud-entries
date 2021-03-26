# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

import requests
import time

from cloudify import ctx
from cloudify.utils import decrypt_password

from abstract_plugin.platforms.common.connector import Connector


class Client(Connector):
    def __init__(self, **kwargs):
        super(Client, self).__init__()
        self.username = self.connection_config.get('username')
        self.password = decrypt_password(self.connection_config.get('password'))
        self.host = self.connection_config.get('host')
        self.port = self.connection_config.get('port')
        self._protocol = self.connection_config.get('protocol')

    def _gen_url(self, path, is_v3=False):
        if path.startswith("/"):
            path = path[1:]

        return "{protocol}://{host}:{port}/api/{version}/{path}".format(
            protocol=self._protocol,
            host=self.host,
            port=self.port,
            version="v3" if is_v3 else "v2",
            path=path
        )

    def get_token(self):
        res = requests.post(
            url=self._gen_url("/sessions", True),
            json={"username": self.username, "password": self.password},
            verify=False
        )
        res.raise_for_status()
        return res.json()["token"]

    def release(self, token):
        if token:
            requests.delete(
                url=self._gen_url("/sessions", True),
                headers={"Grpc-Metadata-Token": token},
                verify=False
            )

    def _call_method(self, method, url, **kwargs):
        def c(tk):
            m = getattr(requests, method)
            r = m(url, headers={"X-SmartX-Token": tk}, verify=False, **kwargs)
            r.raise_for_status()
            return r.json()

        token = kwargs.pop("token", None)
        if not token:
            token = self.get_token()
            try:
                return c(token)
            finally:
                self.release(token)
        else:
            return c(token)

    def post(self, path, data=None, token=None, is_v3=False):
        return self._call_method(
            method="post",
            url=self._gen_url(path, is_v3=is_v3),
            json=data,
            token=token
        )

    def put(self, path, data=None, token=None, is_v3=False):
        return self._call_method(
            method="put",
            url=self._gen_url(path, is_v3=is_v3),
            json=data,
            token=token
        )

    def get(self, path, token=None, is_v3=False, **kwargs):
        return self._call_method(
            method="get",
            url=self._gen_url(path, is_v3=is_v3),
            token=token,
            **kwargs
        )

    def delete(self, path, token=None, is_v3=False, **kwargs):
        return self._call_method(
            method="delete",
            url=self._gen_url(path, is_v3),
            token=token,
            **kwargs
        )


class Helper(object):
    def __init__(self, client):
        self.client = client
        self._token = None

    @staticmethod
    def check_r(r):
        if r.get("ec") != "EOK":
            raise Exception(r)
        return r.get("data")

    def __enter__(self):
        self._token = self.client.get_token()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.release(self._token)
        self._token = None

    def get_job(self, job_id):
        return self.check_r(self.client.get(
            "/jobs/{}".format(job_id), token=self._token
        ))["job"]

    def wait_job(self, job_id):
        ctx.logger.debug('Waiting for job {} to be done.'.format(job_id))
        job = self.get_job(job_id)
        while job["state"] not in ("done", "failed"):
            time.sleep(5)
            job = self.get_job(job_id)
        ctx.logger.debug('Job {} is {}.'.format(job_id, job['state']))
        return job['state']


class NetworkHelper(Helper):
    def __init__(self, client):
        super(NetworkHelper, self).__init__(client)

    def get_vds(self, vds_id):
        return self.check_r(self.client.get("/network/vds/{}".format(vds_id), token=self._token))

    def create_network(self, data):
        vds_id = data.pop('vds_id')

        return self.check_r(self.client.post(
            "/network/vds/{}/vlans".format(vds_id),
            data,
            token=self._token
        ))

    def get_network(self, vds_id, network_id):
        return self.check_r(self.client.get(
            "/network/vds/{}/vlans/{}".format(vds_id, network_id), token=self._token
        ))

    def list_networks(self, ):
        return self.check_r(self.client.get(
            "/network/vm_vlans/search", token=self._token
        ))

    def delete_network(self, vds_id, network_id):
        return self.check_r(self.client.delete(
            "/network/vds/{}/vlans/{}".format(vds_id, network_id), token=self._token
        ))


class VolumeHelper(Helper):
    def __init__(self, client):
        super(VolumeHelper, self).__init__(client)

    def create_volume(self, data):

        return self.check_r(self.client.post(
            "/volumes",
            data,
            token=self._token
        ))

    def get_volume(self, volume_id):
        return self.check_r(self.client.get(
            "/volumes/{}".format(volume_id), token=self._token
        ))

    def update_volume(self, volume_id, data):
        return self.check_r(self.client.put(
            "/volumes/{}".format(volume_id),
            data,
            token=self._token
        ))

    def delete_volume(self, volume_id):
        return self.check_r(self.client.delete(
            "/volumes/{}".format(volume_id), token=self._token
        ))

    def update_disks(self, vm_uuid, disks=[], disk_paths_del=[]):
        """

        [{"type": "disk", "bus": "virtio", "path": "string", "size_in_byte": 0}]

        """

        ctx.logger.debug("Updating disks of vm '{}'".format(vm_uuid))
        return self.check_r(self.client.put(
            "/vms/{}".format(vm_uuid),
            {"disks": disks, "disk_paths_del": disk_paths_del},
            token=self._token
        ))


class ComputeHelper(Helper):
    def __init__(self, client):
        super(ComputeHelper, self).__init__(client)

    def create_vm_from_template(self, data):
        image_id = data.pop('image_id')
        data = {'vms': [data]}
        ctx.logger.debug("Creating vm from template '{}'".format(image_id))
        return self.check_r(self.client.post("/vm_templates/{}/create_vms".format(image_id), data, token=self._token))

    def delete_vm_template(self, vm_template_uuid):
        return self.check_r(self.client.delete(
            "/vm_templates/{}".format(vm_template_uuid), token=self._token
        ))

    def create_vm(self, data):
        ctx.logger.debug('Creating vm with parameters: {}'.format(data))
        return self.check_r(self.client.post("/vms", data, token=self._token))

    def get_vm(self, vm_uuid):
        ctx.logger.debug("Query detail of vm {}.".format(vm_uuid))
        return self.check_r(self.client.get("/vms/{}".format(vm_uuid), token=self._token))

    def delete_vm(self, vm_uuid, data={}):
        ctx.logger.debug('Deleting vm {}'.format(vm_uuid))
        return self.check_r(
            self.client.delete("/vms/{}".format(vm_uuid), data=data, token=self._token))

    def start_vm(self, vm_uuid):
        ctx.logger.debug('Staring vm {}.'.format(vm_uuid))
        return self.check_r(self.client.post(
            "/vms/{}/start".format(vm_uuid), token=self._token
        ))

    def pause_vm(self, vm_uuid):
        ctx.logger.debug('Pausing vm {}.'.format(vm_uuid))
        return self.check_r(self.client.post(
            "/vms/{}/pause".format(vm_uuid), token=self._token
        ))

    def resume_vm(self, vm_uuid):
        ctx.logger.debug('Resuming vm {}'.format(vm_uuid))
        return self.check_r(self.client.post(
            "/vms/{}/resume".format(vm_uuid), token=self._token
        ))

    def stop_vm(self, vm_uuid, force=True):
        ctx.logger.debug('Stopping vm {}.'.format('vm_uuid'))
        return self.check_r(self.client.post(
            "/vms/{}/stop".format(vm_uuid),
            {"force": force},
            token=self._token
        ))

    def reboot_vm(self, vm_uuid, force=True):
        ctx.logger.debug('Rebooting vm {}.'.format(vm_uuid))
        return self.check_r(self.client.post(
            "/vms/{}/reboot".format(vm_uuid),
            {"force": force},
            token=self._token
        ))

    def clone_vm(self, vm_uuid, clone_params):
        ctx.logger.debug("Cloning vm '{}'".format(vm_uuid))
        return self.check_r(self.client.post(
            "/vms/{}/clone".format(vm_uuid), clone_params, token=self._token
        ))

    def migrate_vm(self, vm_uuid, node_ip=None):
        ctx.logger.debug("Migrating vm '{}'".format(vm_uuid))
        if node_ip:
            data = {"node_ip": node_ip}
        else:
            data = {"auto_schedule": True}
        return self.check_r(self.client.post(
            "/vms/{}/migrate".format(vm_uuid), data, token=self._token
        ))

    def update_base_info(self, vm_uuid, data):
        ctx.logger.debug("Updating info of vm '{}'".format(vm_uuid))
        return self.check_r(self.client.put(
            "/vms/{}".format(vm_uuid), data, token=self._token
        ))

    def update_nics(self, vm_uuid, nics):
        ctx.logger.debug("Updating nics of vm '{}'".format(vm_uuid))
        return self.check_r(self.client.put(
            "/vms/{}".format(vm_uuid),
            {"nics": nics},
            token=self._token
        ))

    def modify_display_name(self, vm_uuid, name):
        ctx.logger.debug("Updating display name of vm '{}'".format(vm_uuid))
        vm_info = self.get_vm(vm_uuid)
        return self.check_r(self.client.put(
            "/vms/{}".format(vm_uuid),
            {"vm_name": name, "cpu": vm_info['cpu'], 'ha': vm_info['ha']},
            token=self._token
        ))

    def modify_configure(self, vm_uuid, params):
        ctx.logger.debug("Updating configuration of vm '{}'".format(vm_uuid))
        return self.check_r(self.client.put(
            "/vms/{}".format(vm_uuid), params, token=self._token
        ))
