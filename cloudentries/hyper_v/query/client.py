# Copyright (c) 2021 Qianyun, Inc. All rights reserved.

from base64 import b64encode
from winrm import Response
from winrm import Session


# patch the winrm class Session
# set codepage to 65001(the powershell utf-8 charset code is 65001) to use utf-8 to decode
# extend the timeout period
class SessionUTF8(Session):
    def run_cmd(self, command, args=()):
        self.protocol.DEFAULT_READ_TIMEOUT_SEC = 300
        self.protocol.DEFAULT_OPERATION_TIMEOUT_SEC = 200
        shell_id = self.protocol.open_shell(codepage=65001)
        command_id = self.protocol.run_command(shell_id, command, args)
        rs = Response(self.protocol.get_command_output(shell_id, command_id))
        self.protocol.cleanup_command(shell_id, command_id)
        self.protocol.close_shell(shell_id)
        return rs

    def run_ps(self, script):
        encoded_ps = b64encode(script.encode("utf_16_le")).decode("utf-8")
        rs = self.run_cmd(f"powershell -encodedcommand {encoded_ps}")
        if len(rs.std_err):
            rs.std_err = self._clean_error_msg(rs.std_err)
        return rs


class HyperVClient:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def run(self, script):
        try:
            client = SessionUTF8(
                self.url, auth=(self.username, self.password), transport="ntlm"
            )
            r = client.run_ps(script)
            return r.status_code, r.std_out.decode("utf-8"), r.std_err
        except Exception as e:
            raise Exception(
                "Execute script failed! script is : {}, the error message is {}".format(
                    script, e
                )
            )
