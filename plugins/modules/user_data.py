#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: user_data
short_description: Manages user data on Apache CloudStack based clouds.
description:
  - Create and remove user data records.
  - Updating existing user data is not supported by the CloudStack API.
  - When the requested values differ from an existing record, the module keeps the existing record and shows a warning.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  name:
    description:
      - Name of the user data record.
    type: str
    required: true
  user_data:
    description:
      - User data content to register.
      - Required on I(state=present).
      - Only considered on creation and will not be updated if the user data record already exists.
    type: str
    aliases: [ userdata ]
  params:
    description:
      - List of variables declared in the user data content.
      - Only considered on creation and will not be updated if the user data record already exists.
    type: list
    elements: str
  domain:
    description:
      - Domain the user data is related to.
    type: str
  account:
    description:
      - Account the user data is related to.
    type: str
  project:
    description:
      - Project the user data is related to.
    type: str
  state:
    description:
      - State of the user data record.
    type: str
    default: present
    choices: [ present, absent ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Create registered user data
  ngine_io.cloudstack.user_data:
    name: cloud-init-basic
    user_data: |
      #cloud-config
      package_upgrade: true
      packages:
        - tmux

- name: Create registered user data with declared variables
  ngine_io.cloudstack.user_data:
    name: bootstrap-template
    user_data: |
      #!/bin/sh
      echo ${hostname} >/etc/hostname
    params:
      - hostname

- name: Remove registered user data
  ngine_io.cloudstack.user_data:
    name: cloud-init-basic
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the user data record.
  returned: success
  type: str
  sample: 119aa0be-67bc-41d5-9e3f-3660c44f90f0
name:
  description: Name of the user data record.
  returned: success
  type: str
  sample: cloud-init-basic
account:
  description: Account that owns the user data record.
  returned: success
  type: str
  sample: admin
domain:
  description: Domain that owns the user data record.
  returned: success
  type: str
  sample: ROOT
project:
  description: Project that owns the user data record.
  returned: success
  type: str
  sample: sample-project
params:
  description: Declared variables for the registered user data.
  returned: success
  type: list
  elements: str
  sample: [ hostname ]
user_data:
  description: Decoded user data content.
  returned: success
  type: str
  sample: "#cloud-config\\npackage_upgrade: true\\n"
"""

import base64

from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackUserData(AnsibleCloudStack):
    """AnsibleCloudStackUserData"""

    def __init__(self, module):
        super(AnsibleCloudStackUserData, self).__init__(module)
        self.returns = {
            "params": "params",
            "userdata": "user_data",
        }
        self.user_data = None

    def _decode_user_data(self, user_data):
        if user_data is None:
            return None
        return to_text(base64.b64decode(to_bytes(user_data)))

    def _encode_user_data(self):
        user_data = self.module.params.get("user_data")
        if user_data is None:
            return None
        return to_text(base64.b64encode(to_bytes(user_data)))

    def _normalize_params(self, params):
        if params in [None, ""]:
            return []
        if isinstance(params, list):
            return params
        return [param.strip() for param in params.split(",") if param.strip()]

    def _normalize_user_data(self, user_data):
        if not user_data:
            return user_data

        user_data = user_data.copy()
        if "userdata" in user_data:
            user_data["userdata"] = self._decode_user_data(user_data["userdata"])
        if "params" in user_data:
            user_data["params"] = self._normalize_params(user_data["params"])
        return user_data

    def _get_desired_user_data(self):
        params = self.module.params.get("params")
        if params is not None:
            params = sorted(params)

        return {
            "name": self.module.params.get("name"),
            "userdata": self.module.params.get("user_data"),
            "params": params,
        }

    def _get_current_user_data(self, user_data):
        params = user_data.get("params")
        if params is not None or self.module.params.get("params") is not None:
            params = sorted(self._normalize_params(params))

        return {
            "name": user_data.get("name"),
            "userdata": user_data.get("userdata"),
            "params": params,
        }

    def get_user_data(self, refresh=False):
        if self.user_data is not None and not refresh:
            return self.user_data

        self.user_data = None
        name = self.module.params.get("name")

        args = {
            "name": name,
            "account": self.get_account(key="name"),
            "domainid": self.get_domain(key="id"),
            "projectid": self.get_project(key="id"),
            "listall": True,
            "fetch_list": True,
        }
        user_data_list = self.query_api("listUserData", **args)
        if user_data_list:
            self.user_data = self._normalize_user_data(user_data_list[0])

        return self.user_data

    def present_user_data(self):
        user_data = self.get_user_data()
        if not user_data:
            self.result["changed"] = True

            args = {
                "name": self.module.params.get("name"),
                "userdata": self._encode_user_data(),
                "account": self.get_account(key="name"),
                "domainid": self.get_domain(key="id"),
                "projectid": self.get_project(key="id"),
            }
            params = self.module.params.get("params")
            if params:
                args["params"] = ",".join(params)

            if not self.module.check_mode:
                self.query_api("registerUserData", **args)
                user_data = self.get_user_data(refresh=True)
                if not user_data:
                    self.fail_json(msg="User data '%s' was registered but could not be retrieved afterwards" % self.module.params.get("name"))
            return user_data

        desired_user_data = self._get_desired_user_data()
        current_user_data = self._get_current_user_data(user_data)
        if self.has_changed(desired_user_data, current_user_data):
            self.module.warn(
                "User data '%s' already exists but differs from the requested values. Updating registered user data is not supported by the CloudStack API, so the existing record was left unchanged."
                % self.module.params.get("name")
            )
        return user_data

    def absent_user_data(self):
        user_data = self.get_user_data()
        if user_data:
            self.result["changed"] = True
            if not self.module.check_mode:
                self.query_api(
                    "deleteUserData",
                    id=user_data["id"],
                    account=self.get_account(key="name"),
                    domainid=self.get_domain(key="id"),
                    projectid=self.get_project(key="id"),
                )
        return user_data


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(required=True),
            user_data=dict(type="str", aliases=["userdata"]),
            params=dict(type="list", elements="str"),
            state=dict(default="present", choices=["present", "absent"]),
            domain=dict(type="str"),
            account=dict(type="str"),
            project=dict(type="str"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "present", ["user_data"]),
        ],
        supports_check_mode=True,
    )

    acs_user_data = AnsibleCloudStackUserData(module)

    state = module.params.get("state")
    if state == "absent":
        user_data = acs_user_data.absent_user_data()
    else:
        user_data = acs_user_data.present_user_data()

    result = acs_user_data.get_result(user_data)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
