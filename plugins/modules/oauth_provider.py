#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: oauth_provider
short_description: Manages OAuth providers on Apache CloudStack based clouds.
description:
    - Register, update and delete OAuth2 providers.
author: René Moser (@resmo)
version_added: 3.3.0
options:
  name:
    description:
      - Name of the OAuth provider (maps to the provider identifier, e.g. C(google), C(github)).
    type: str
    required: true
  description:
    description:
      - Description of the OAuth provider.
      - Required when I(state=present).
    type: str
  client_id:
    description:
      - Client ID pre-registered in the OAuth provider.
      - Required when I(state=present).
    type: str
  secret_key:
    description:
      - Secret key pre-registered in the OAuth provider.
      - Required when I(state=present).
    type: str
  redirect_uri:
    description:
      - Redirect URI pre-registered in the OAuth provider.
      - Required when I(state=present).
    type: str
  enabled:
    description:
      - Whether the OAuth provider is enabled.
    type: bool
    default: true
  token_url:
    description:
      - Token URL of the OAuth provider.
      - Ignored unless CloudStack >=4.23.
    type: str
  authorized_url:
    description:
      - Authorized URL of the OAuth provider.
      - Ignored unless CloudStack >=4.23.
    type: str
  details:
    description:
      - List of additional key/value pairs for the OAuth provider.
      - Only used when I(state=present) while creating the OAuth provider.
      - CloudStack API does not support updating the details of an existing OAuth provider.
    type: list
    elements: dict
  domain:
    description:
      - Domain the SSL certificate is related to.
    type: str
  state:
    description:
      - State of the OAuth provider.
    type: str
    default: present
    choices: [ present, absent ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Register an OAuth provider
  ngine_io.cloudstack.oauth_provider:
    name: google
    description: Google OAuth2
    client_id: "my-client-id.apps.googleusercontent.com"
    details:
      scope: "openid email profile"
      clientsecret: "my secret key"
    secret_key: "my-secret-key"
    redirect_uri: "https://cloudstack.example.com/client/api?command=oauthlogin&source=google"

- name: Disable an OAuth provider
  ngine_io.cloudstack.oauth_provider:
    name: google
    description: Google OAuth2
    client_id: "my-client-id.apps.googleusercontent.com"
    secret_key: "my-secret-key"
    redirect_uri: "https://cloudstack.example.com/client/api?command=oauthlogin&source=google"
    enabled: false

- name: Delete an OAuth provider
  ngine_io.cloudstack.oauth_provider:
    name: google
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the OAuth provider.
  returned: success
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
name:
  description: Name of the OAuth provider.
  returned: success
  type: str
  sample: google
description:
  description: Description of the OAuth provider.
  returned: success
  type: str
  sample: Google OAuth2
client_id:
  description: Client ID registered in the OAuth provider.
  returned: success
  type: str
  sample: "my-client-id.apps.googleusercontent.com"
redirect_uri:
  description: Redirect URI registered in the OAuth provider.
  returned: success
  type: str
  sample: "https://cloudstack.example.com/client/api?command=oauthlogin&source=google"
enabled:
  description: Whether the OAuth provider is enabled.
  returned: success
  type: bool
  sample: true
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackOauthProvider(AnsibleCloudStack):
    """AnsibleCloudStackOauthProvider"""

    def __init__(self, module):
        super(AnsibleCloudStackOauthProvider, self).__init__(module)
        self.returns = {
            "provider": "name",
            "clientid": "client_id",
            "redirecturi": "redirect_uri",
            "tokenurl": "token_url",
            "authorizedurl": "authorized_url",
            "enabled": "enabled",
        }
        self.oauth_provider = None

    def get_oauth_provider(self, refresh=False):
        if not self.oauth_provider or refresh:
            provider_name = self.module.params.get("name")
            res = self.query_api("listOauthProvider", provider=provider_name)
            if res and "oauthprovider" in res:
                self.oauth_provider = res["oauthprovider"][0]
        return self.oauth_provider

    def present_oauth_provider(self):
        oauth_provider = self.get_oauth_provider()
        if not oauth_provider:
            oauth_provider = self._register_oauth_provider()

            # CloudStack API does not allow to disable an OAuth provider during registration, so we need to update it afterwards if the user wants it disabled.
            if oauth_provider is not None and oauth_provider.get("enabled", True) != self.module.params.get("enabled"):
                oauth_provider = self._update_oauth_provider(oauth_provider)
        else:
            oauth_provider = self._update_oauth_provider(oauth_provider)
        return oauth_provider

    def _register_oauth_provider(self):
        self.result["changed"] = True
        if not self.module.check_mode:
            args = {
                "provider": self.module.params.get("name"),
                "description": self.module.params.get("description"),
                "clientid": self.module.params.get("client_id"),
                "secretkey": self.module.params.get("secret_key"),
                "redirecturi": self.module.params.get("redirect_uri"),
                "details": self.module.params.get("details"),
                "enabled": self.module.params.get("enabled"),
                # CloudStack >=4.23 supports authorized_url and token_url parameters for OAuth providers.
                "authorizedurl": self.module.params.get("authorized_url"),
                "tokenurl": self.module.params.get("token_url"),
            }
            self.query_api("registerOauthProvider", **args)
            # registerOauthProvider returns only success/displaytext, fetch the object
            self.oauth_provider = None
            return self.get_oauth_provider()
        return None

    def _update_oauth_provider(self, oauth_provider):
        args = {
            "id": oauth_provider["id"],
            "description": self.module.params.get("description"),
            "clientid": self.module.params.get("client_id"),
            "redirecturi": self.module.params.get("redirect_uri"),
            "secretkey": self.module.params.get("secret_key"),
            "enabled": self.module.params.get("enabled"),
            # CloudStack >=4.23 supports authorized_url and token_url parameters for OAuth providers.
            "authorizedurl": self.module.params.get("authorized_url"),
            "tokenurl": self.module.params.get("token_url"),
        }

        if self.has_changed(args, oauth_provider):
            self.result["changed"] = True
            if not self.module.check_mode:
                self.query_api("updateOauthProvider", **args)
                oauth_provider = self.get_oauth_provider(refresh=True)
        return oauth_provider

    def absent_oauth_provider(self):
        oauth_provider = self.get_oauth_provider()
        if oauth_provider:
            self.result["changed"] = True
            if not self.module.check_mode:
                self.query_api("deleteOauthProvider", id=oauth_provider["id"])
        return oauth_provider


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            description=dict(type="str"),
            client_id=dict(type="str"),
            secret_key=dict(type="str", no_log=True),
            redirect_uri=dict(type="str"),
            enabled=dict(type="bool", default=True),
            domain=dict(type="str"),
            authorized_url=dict(type="str"),
            token_url=dict(type="str", no_log=False),
            details=dict(type="list", elements="dict"),
            state=dict(choices=["present", "absent"], default="present"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "present", ["description", "client_id", "secret_key", "redirect_uri"]),
        ],
        supports_check_mode=True,
    )

    acs_oauth_provider = AnsibleCloudStackOauthProvider(module)
    state = module.params.get("state")
    if state == "absent":
        oauth_provider = acs_oauth_provider.absent_oauth_provider()
    else:
        oauth_provider = acs_oauth_provider.present_oauth_provider()

    result = acs_oauth_provider.get_result(oauth_provider)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
