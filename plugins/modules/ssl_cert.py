#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: ssl_cert
short_description: Manages SSL certificates on Apache CloudStack based clouds.
description:
    - Upload and remove SSL certificates.
author: René Moser (@resmo)
version_added: 3.2.0
options:
  name:
    description:
      - Name of the SSL certificate.
    type: str
    required: true
  certificate:
    description:
      - SSL certificate.
      - Required when I(state=present).
    type: str
  private_key:
    description:
      - Private key for the SSL certificate.
      - Required when I(state=present).
    type: str
  cert_chain:
    description:
      - Certificate chain of trust.
    type: str
  password:
    description:
      - Password for the private key.
    type: str
  enable_revocation_check:
    description:
      - Whether to enable revocation checking for the certificate.
    type: bool
  force:
    description:
      - Whether to force recreation of the SSL certificate if a certificate with the same name already exists.
    type: bool
    default: false
  domain:
    description:
      - Domain the SSL certificate is related to.
    type: str
  account:
    description:
      - Account the SSL certificate is related to.
    type: str
  project:
    description:
      - Name of the project the SSL certificate is related to.
    type: str
  state:
    description:
      - State of the SSL certificate.
    type: str
    default: present
    choices: [ present, absent ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Upload an SSL certificate
  ngine_io.cloudstack.ssl_cert:
    name: my-ssl-cert
    certificate: "{{ lookup('file', 'cert.pem') }}"
    private_key: "{{ lookup('file', 'key.pem') }}"

- name: Upload an SSL certificate with a certificate chain
  ngine_io.cloudstack.ssl_cert:
    name: my-ssl-cert
    certificate: "{{ lookup('file', 'cert.pem') }}"
    private_key: "{{ lookup('file', 'key.pem') }}"
    cert_chain: "{{ lookup('file', 'chain.pem') }}"

- name: Remove an SSL certificate
  ngine_io.cloudstack.ssl_cert:
    name: my-ssl-cert
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the SSL certificate.
  returned: success
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
name:
  description: Name of the SSL certificate.
  returned: success
  type: str
  sample: my-ssl-cert
certificate:
  description: SSL certificate.
  returned: success
  type: str
  sample: "-----BEGIN CERTIFICATE-----\\n...\\n-----END CERTIFICATE-----\\n"
cert_chain:
  description: Certificate chain of trust.
  returned: success
  type: str
  sample: "-----BEGIN CERTIFICATE-----\\n...\\n-----END CERTIFICATE-----\\n"
fingerprint:
  description: Fingerprint of the SSL certificate.
  returned: success
  type: str
  sample: "68:82:16:b8:f6:e6:d8:52:08:21:ac:39:23:8c:3a:53:62:77:90:aa:fb:8f:0c:37:71:c2:a1:10:c9:b2:19:04"
account:
  description: Account the SSL certificate is related to.
  returned: success
  type: str
  sample: example account
domain:
  description: Domain the SSL certificate is related to.
  returned: success
  type: str
  sample: example domain
project:
  description: Project the SSL certificate is related to.
  returned: success
  type: str
  sample: Production
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackSslCert(AnsibleCloudStack):
    """AnsibleCloudStackSslCert"""

    def __init__(self, module):
        super(AnsibleCloudStackSslCert, self).__init__(module)
        self.returns = {
            "certificate": "certificate",
            "certchain": "cert_chain",
            "fingerprint": "fingerprint",
        }
        self.ssl_cert = None

    def get_ssl_cert(self):
        if not self.ssl_cert:
            # Inconsitent API, accountid instead of account with domainid
            args = {
                "projectid": self.get_project(key="id"),
                "accountid": self.get_account(key="id", use_fallback=True),
            }
            res = self.query_api("listSslCerts", **args)
            if res and "sslcert" in res:
                name = self.module.params.get("name")
                for cert in res["sslcert"]:
                    if cert.get("name").lower() == name.lower():
                        self.ssl_cert = cert
                        break
        return self.ssl_cert

    def present_ssl_cert(self):
        required_params = ["certificate", "private_key"]
        self.module.fail_on_missing_params(required_params=required_params)

        ssl_cert = self.get_ssl_cert()
        if not ssl_cert:
            ssl_cert = self._upload_ssl_cert()
        else:
            args = {
                "certificate": self.module.params.get("certificate"),
                "privatekey": self.module.params.get("private_key"),
                "certchain": self.module.params.get("cert_chain"),
            }
            if self.has_changed(args, ssl_cert):
                if not self.module.params.get("force"):
                    self.module.warn(
                        "SSL certificate name already exists but its content is different. "
                        "Use 'force=true' to delete and reupload it with the same name but different ID."
                    )
                else:
                    self.result["changed"] = True
                    if not self.module.check_mode:
                        self.query_api("deleteSslCert", id=ssl_cert["id"])
                        ssl_cert = self._upload_ssl_cert()

        return ssl_cert

    def _upload_ssl_cert(self):
        self.result["changed"] = True
        ssl_cert = None
        if not self.module.check_mode:
            args = {
                "name": self.module.params.get("name"),
                "certificate": self.module.params.get("certificate"),
                "privatekey": self.module.params.get("private_key"),
                "certchain": self.module.params.get("cert_chain"),
                "password": self.module.params.get("password"),
                "account": self.get_account(key="name"),
                "domainid": self.get_domain(key="id"),
                "projectid": self.get_project(key="id"),
            }
            if self.module.params.get("enable_revocation_check") is not None:
                args["enabledrevocationcheck"] = self.module.params.get("enable_revocation_check")

            res = self.query_api("uploadSslCert", **args)
            if res and "sslcert" in res:
                ssl_cert = res["sslcert"]
        return ssl_cert

    def absent_ssl_cert(self):
        ssl_cert = self.get_ssl_cert()
        if ssl_cert:
            self.result["changed"] = True
            if not self.module.check_mode:
                self.query_api("deleteSslCert", id=ssl_cert["id"])
        return ssl_cert


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(required=True),
            certificate=dict(),
            private_key=dict(no_log=True),
            cert_chain=dict(),
            password=dict(no_log=True),
            enable_revocation_check=dict(type="bool"),
            domain=dict(),
            account=dict(),
            project=dict(),
            force=dict(type="bool", default=False),
            state=dict(choices=["present", "absent"], default="present"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "present", ["certificate", "private_key"]),
        ],
        supports_check_mode=True,
    )

    acs_ssl_cert = AnsibleCloudStackSslCert(module)
    state = module.params.get("state")
    if state == "absent":
        ssl_cert = acs_ssl_cert.absent_ssl_cert()
    else:
        ssl_cert = acs_ssl_cert.present_ssl_cert()

    result = acs_ssl_cert.get_result(ssl_cert)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
