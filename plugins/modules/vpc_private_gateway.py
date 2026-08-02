#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: vpc_private_gateway
short_description: Manages private gateways for VPCs on Apache CloudStack based clouds.
description:
    - Create and remove private gateways attached to a VPC.
    - Existing private gateways are matched by IP address within the VPC scope.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  vpc:
    description:
      - Name of the VPC.
    type: str
    required: true
  ip_address:
    description:
      - IP address of the private gateway.
    type: str
    required: true
  gateway:
    description:
      - Gateway of the private gateway.
      - Required on I(state=present).
    type: str
  netmask:
    description:
      - Netmask of the private gateway.
      - Required on I(state=present).
    type: str
  vlan:
    description:
      - VLAN identifier or URI of the private gateway.
      - Required on I(state=present).
    type: str
  zone:
    description:
      - Name of the zone the VPC belongs to.
    type: str
    required: true
  physical_network:
    description:
      - Name of the physical network the private gateway belongs to.
    type: str
  network:
    description:
      - Name of the isolated network this private gateway is associated with.
    type: str
  network_acl:
    description:
      - Name of the network ACL to attach to the private gateway.
    type: str
  network_offering:
    description:
      - Network offering to use for the private gateway network connection.
    type: str
  bypass_vlan_overlap_check:
    description:
      - Whether to bypass VLAN overlap checks during creation.
    type: bool
  source_nat_supported:
    description:
      - Whether source NAT should be enabled on the private gateway.
    type: bool
  domain:
    description:
      - Domain the private gateway is related to.
    type: str
  account:
    description:
      - Account the private gateway is related to.
    type: str
  project:
    description:
      - Name of the project the private gateway is related to.
    type: str
  state:
    description:
      - State of the private gateway.
    type: str
    default: present
    choices: [ present, absent ]
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: true
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure a private gateway is present on a VPC
  ngine_io.cloudstack.vpc_private_gateway:
    vpc: my-vpc
    zone: zone01
    ip_address: 10.11.11.2
    gateway: 10.11.11.1
    netmask: 255.255.255.0
    vlan: "400"

- name: Ensure a private gateway is absent from a VPC
  ngine_io.cloudstack.vpc_private_gateway:
    vpc: my-vpc
    zone: zone01
    ip_address: 10.11.11.2
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the private gateway.
  returned: success
  type: str
  sample: 04589590-ac63-4ffc-93f5-b698b8ac38b6
ip_address:
  description: IP address of the private gateway.
  returned: success
  type: str
  sample: 10.11.11.2
gateway:
  description: Gateway of the private gateway.
  returned: success
  type: str
  sample: 10.11.11.1
netmask:
  description: Netmask of the private gateway.
  returned: success
  type: str
  sample: 255.255.255.0
vlan:
  description: VLAN identifier or URI of the private gateway.
  returned: success
  type: str
  sample: "400"
vpc:
  description: Name of the VPC the private gateway belongs to.
  returned: success
  type: str
  sample: my-vpc
vpc_id:
  description: UUID of the VPC the private gateway belongs to.
  returned: success
  type: str
  sample: 87b1e0ce-4e01-11e4-bb66-0050569e64b8
network_acl:
  description: Name of the ACL associated with the private gateway.
  returned: when available
  type: str
  sample: default-vpc-acl
network_acl_id:
  description: UUID of the ACL associated with the private gateway.
  returned: when available
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
source_nat_supported:
  description: Whether source NAT is supported on the private gateway.
  returned: success
  type: bool
  sample: false
state:
  description: State of the private gateway.
  returned: success
  type: str
  sample: Ready
zone:
  description: Name of the zone the private gateway belongs to.
  returned: success
  type: str
  sample: Sandbox-simulator-advanced
project:
  description: Name of the project the private gateway is related to.
  returned: when available
  type: str
  sample: Production
account:
  description: Account the private gateway is related to.
  returned: when available
  type: str
  sample: example-account
domain:
  description: Domain the private gateway is related to.
  returned: when available
  type: str
  sample: ROOT
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackVpcPrivateGateway(AnsibleCloudStack):
    """AnsibleCloudStackVpcPrivateGateway"""

    def __init__(self, module):
        super(AnsibleCloudStackVpcPrivateGateway, self).__init__(module)
        self.private_gateway = None
        self.returns = {
            "aclid": "network_acl_id",
            "aclname": "network_acl",
            "gateway": "gateway",
            "ipaddress": "ip_address",
            "netmask": "netmask",
            "physicalnetworkid": "physical_network_id",
            "sourcenatsupported": "source_nat_supported",
            "vlan": "vlan",
            "vpcid": "vpc_id",
            "vpcname": "vpc",
        }

    def get_network_offering(self, key=None):
        network_offering = self.module.params.get("network_offering")
        if not network_offering:
            return None

        args = {
            "zoneid": self.get_zone(key="id"),
            "fetch_list": True,
        }
        network_offerings = self.query_api("listNetworkOfferings", **args)
        if network_offerings:
            for offering in network_offerings:
                if network_offering in [offering["name"], offering["displaytext"], offering["id"]]:
                    return self._get_by_key(key, offering)
        self.fail_json(msg="Network offering '%s' not found" % network_offering)

    def _get_common_args(self):
        args = {
            "account": self.get_account(key="name"),
            "domainid": self.get_domain(key="id"),
            "ipaddress": self.module.params.get("ip_address"),
            "projectid": self.get_project(key="id"),
            "vpcid": self.get_vpc(key="id"),
        }
        return args

    def get_private_gateway(self):
        if not self.private_gateway:
            args = self._get_common_args()
            args["fetch_list"] = True
            private_gateways = self.query_api("listPrivateGateways", **args)
            if private_gateways:
                for private_gateway in private_gateways:
                    if private_gateway["ipaddress"] == self.module.params.get("ip_address"):
                        self.private_gateway = private_gateway
                        break
        return self.private_gateway

    def present_private_gateway(self):
        self.module.fail_on_missing_params(required_params=["gateway", "netmask", "vlan"])

        private_gateway = self.get_private_gateway()
        if not private_gateway:
            self.result["changed"] = True
            args = self._get_common_args()
            args.update(
                {
                    "aclid": self.get_network_acl(key="id") if self.module.params.get("network_acl") else None,
                    "associatednetworkid": self.get_network(key="id") if self.module.params.get("network") else None,
                    "bypassvlanoverlapcheck": self.module.params.get("bypass_vlan_overlap_check"),
                    "gateway": self.module.params.get("gateway"),
                    "netmask": self.module.params.get("netmask"),
                    "networkofferingid": self.get_network_offering(key="id"),
                    "physicalnetworkid": self.get_physical_network(key="id") if self.module.params.get("physical_network") else None,
                    "sourcenatsupported": self.module.params.get("source_nat_supported"),
                    "vlan": self.module.params.get("vlan"),
                }
            )

            if not self.module.check_mode:
                res = self.query_api("createPrivateGateway", **args)
                poll_async = self.module.params.get("poll_async")
                if poll_async:
                    private_gateway = self.poll_job(res, "privategateway")

        self.private_gateway = private_gateway
        return private_gateway

    def absent_private_gateway(self):
        private_gateway = self.get_private_gateway()
        if private_gateway:
            self.result["changed"] = True
            if not self.module.check_mode:
                res = self.query_api("deletePrivateGateway", id=private_gateway["id"])
                poll_async = self.module.params.get("poll_async")
                if poll_async:
                    self.poll_job(res)
        return private_gateway


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            account=dict(type="str"),
            bypass_vlan_overlap_check=dict(type="bool"),
            domain=dict(type="str"),
            gateway=dict(type="str"),
            ip_address=dict(type="str", required=True),
            netmask=dict(type="str"),
            network=dict(type="str"),
            network_acl=dict(type="str"),
            network_offering=dict(type="str"),
            physical_network=dict(type="str"),
            poll_async=dict(type="bool", default=True),
            project=dict(type="str"),
            source_nat_supported=dict(type="bool"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            vlan=dict(type="str"),
            vpc=dict(type="str", required=True),
            zone=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "present", ["gateway", "netmask", "vlan"]),
        ],
        supports_check_mode=True,
    )

    acs_private_gateway = AnsibleCloudStackVpcPrivateGateway(module)

    state = module.params.get("state")
    if state == "absent":
        private_gateway = acs_private_gateway.absent_private_gateway()
    else:
        private_gateway = acs_private_gateway.present_private_gateway()

    result = acs_private_gateway.get_result(private_gateway)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
