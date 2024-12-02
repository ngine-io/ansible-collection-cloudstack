# -*- coding: utf-8 -*-
# Copyright (c) 2024, Lorenzo Tanganelli
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


import os
import re
import sys
import traceback

from ansible.module_utils._text import to_native
from ansible.module_utils.basic import missing_required_lib, AnsibleModule

CS_IMP_ERR = None
try:
    from cs import CloudStack, CloudStackException

    HAS_LIB_CS = True
except ImportError:
    CS_IMP_ERR = traceback.format_exc()
    HAS_LIB_CS = False


if sys.version_info > (3,):
    long = int


class AnsibleCloudStackAPI(AnsibleModule):

    error_callback = None
    warn_callback = None
    AUTH_ARGSPEC = dict(
        api_key=os.getenv("CLOUDSTACK_KEY"),
        api_secret=os.getenv("CLOUDSTACK_SECRET"),
        api_url=os.getenv("CLOUDSTACK_ENDPOINT"),
        api_http_method=os.getenv("CLOUDSTACK_METHOD", "get"),
        api_timeout=os.getenv("CLOUDSTACK_TIMEOUT", 10),
        api_verify_ssl_cert=os.getenv("CLOUDSTACK_VERIFY"),
        validate_certs=os.getenv("CLOUDSTACK_DANGEROUS_NO_TLS_VERIFY", True),
    )

    def __init__(self, argument_spec=None, direct_params=None, error_callback=None, warn_callback=None, **kwargs):

        if not HAS_LIB_CS:
            self.fail_json(msg=missing_required_lib("cs"), exception=CS_IMP_ERR)

        full_argspec = {}
        full_argspec.update(AnsibleCloudStackAPI.AUTH_ARGSPEC)
        full_argspec.update(argument_spec)
        kwargs["supports_check_mode"] = True

        self.error_callback = error_callback
        self.warn_callback = warn_callback

        self._cs = None
        self.result = {}

        if direct_params is not None:
            for param, value in full_argspec.items():
                if param in direct_params:
                    setattr(self, param, direct_params[param])
                else:
                    setattr(self, param, value)
        else:
            super(AnsibleCloudStackAPI, self).__init__(argument_spec=full_argspec, **kwargs)

        # Perform some basic validation
        if not re.match("^https{0,1}://", self.api_url):
            self.api_url = "https://{0}".format(self.api_url)

    def fail_json(self, **kwargs):
        if self.error_callback:
            self.error_callback(**kwargs)
        else:
            super().fail_json(**kwargs)

    def exit_json(self, **kwargs):
        super().exit_json(**kwargs)

    @property
    def cs(self):
        if self._cs is None:
            api_config = self.get_api_config()
            self._cs = CloudStack(**api_config)
        return self._cs

    def get_api_config(self):
        api_config = {
            "endpoint": self.api_url,
            "key": self.api_key,
            "secret": self.api_secret,
            "timeout": self.api_timeout,
            "method": self.api_http_method,
            "verify": self.api_verify_ssl_cert,
            "dangerous_no_tls_verify": not self.validate_certs,
        }

        return api_config

    def query_api(self, command, **args):

        try:
            res = getattr(self.cs, command)(**args)

            if "errortext" in res:
                self.fail_json(msg="Failed: '%s'" % res["errortext"])

        except CloudStackException as e:
            self.fail_json(msg="CloudStackException: %s" % to_native(e))

        except Exception as e:
            self.fail_json(msg=to_native(e))

        # res.update({'params': self.result, 'query_params': args})
        return res
