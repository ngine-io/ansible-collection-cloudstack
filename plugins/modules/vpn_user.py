#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: vpn_user
short_description: Manages VPN users on Apache CloudStack based clouds.
description:
    - Create and remove VPN users.
    - Passwords are only used during creation and are not updated afterwards.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  username:
    description:
      - Username of the VPN user.
    type: str
    required: true
  password:
    description:
      - Password of the VPN user.
      - Required on I(state=present).
      - Only considered on creation and will not be updated if the VPN user already exists.
    type: str
  account:
    description:
      - Account the VPN user is related to.
      - Must be used together with I(domain).
    type: str
  domain:
    description:
      - Domain the VPN user is related to.
    type: str
  project:
    description:
      - Name of the project the VPN user is related to.
    type: str
  state:
    description:
      - State of the VPN user.
    type: str
    default: present
    choices: [ present, absent ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure a VPN user is present for an account
  ngine_io.cloudstack.vpn_user:
    username: johndoe
    password: S3Cur3
    account: developers
    domain: ROOT

- name: Ensure a VPN user is absent for an account
  ngine_io.cloudstack.vpn_user:
    username: johndoe
    account: developers
    domain: ROOT
    state: absent

- name: Ensure a project VPN user is present
  ngine_io.cloudstack.vpn_user:
    username: ci-user
    password: S3Cur3
    project: Production
"""

RETURN = """
---
id:
  description: UUID of the VPN user.
  returned: success
  type: str
  sample: 87b1e0ce-4e01-11e4-bb66-0050569e64b8
username:
  description: Username of the VPN user.
  returned: success
  type: str
  sample: johndoe
account:
  description: Account of the VPN user.
  returned: success
  type: str
  sample: developers
domain:
  description: Domain of the VPN user.
  returned: success
  type: str
  sample: ROOT
project:
  description: Project of the VPN user.
  returned: success
  type: str
  sample: Production
state:
  description: State of the VPN user.
  returned: success
  type: str
  sample: Active
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackVpnUser(AnsibleCloudStack):
    """AnsibleCloudStackVpnUser"""

    def __init__(self, module):
        super(AnsibleCloudStackVpnUser, self).__init__(module)
        self.returns = {
            "username": "username",
        }
        self.vpn_user = None

    def _get_common_args(self):
        return {
            "username": self.module.params.get("username"),
            "projectid": self.get_project("id"),
            "account": self.get_account("name"),
            "domainid": self.get_domain("id"),
        }

    def get_vpn_user(self):
        if not self.vpn_user:
            vpn_users = self.query_api("listVpnUsers", **self._get_common_args())
            if vpn_users:
                self.vpn_user = vpn_users["vpnuser"][0]
        return self.vpn_user

    def present_vpn_user(self):
        self.module.fail_on_missing_params(required_params=["password"])

        vpn_user = self.get_vpn_user()
        if not vpn_user:
            self.result["changed"] = True
            args = self._get_common_args()
            args["password"] = self.module.params.get("password")

            if not self.module.check_mode:
                self.query_api("addVpnUser", **args)
                self.vpn_user = None
                vpn_user = self.get_vpn_user()

        self.vpn_user = vpn_user
        return vpn_user

    def absent_vpn_user(self):
        vpn_user = self.get_vpn_user()
        if vpn_user:
            self.result["changed"] = True
            if not self.module.check_mode:
                self.query_api("removeVpnUser", **self._get_common_args())
            self.vpn_user = vpn_user
        return vpn_user


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            username=dict(type="str", required=True),
            password=dict(type="str", no_log=True),
            account=dict(type="str"),
            domain=dict(type="str"),
            project=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        )
    )

    module = AnsibleModule(argument_spec=argument_spec, required_together=cs_required_together(), supports_check_mode=True)

    acs_vpn_user = AnsibleCloudStackVpnUser(module)

    state = module.params.get("state")
    if state == "absent":
        vpn_user = acs_vpn_user.absent_vpn_user()
    else:
        vpn_user = acs_vpn_user.present_vpn_user()

    result = acs_vpn_user.get_result(vpn_user)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
