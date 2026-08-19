#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, Mitch Drage <mitch@lsnetworks.com.au>
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: internal_lb_vm
short_description: Manages internal load balancer instances on Apache CloudStack based clouds.
description:
    - Start and stop the C(InternalLbVm) system instance which serves the internal load
      balancers of a VPC tier.
    - The instance itself can not be created or destroyed through this API family. CloudStack
      deploys it automatically once the first member is assigned to an internal load balancer,
      see M(ngine_io.cloudstack.lb_internal_member).
author: Mitch Drage (@MitchDrage)
version_added: 3.3.0
options:
  name:
    description:
      - Name of the internal load balancer instance, e.g. C(b-1234-VM).
      - Mutually sufficient with I(network) and I(vpc), at least one of them is required.
    type: str
  network:
    description:
      - Name of the VPC tier the internal load balancer instance serves.
    type: str
  vpc:
    description:
      - Name of the VPC the internal load balancer instance belongs to.
      - Also scopes the I(network) lookup.
    type: str
  zone:
    description:
      - Name of the zone the internal load balancer instance is in.
    type: str
    required: true
  domain:
    description:
      - Domain the internal load balancer instance is related to.
    type: str
  account:
    description:
      - Account the internal load balancer instance is related to.
    type: str
  project:
    description:
      - Name of the project the internal load balancer instance is related to.
    type: str
  state:
    description:
      - State of the internal load balancer instance.
    type: str
    default: started
    choices: [ started, stopped ]
  force:
    description:
      - Whether to force stop the instance.
      - Only considered on I(state=stopped).
    type: bool
    default: false
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: true
notes:
  - This module uses admin only APIs. A regular user account gets an empty result from
    C(listInternalLoadBalancerVMs) and the module will not find the instance.
  - There is no API to create or destroy an internal load balancer instance, so this module
    provides no I(state=present) or I(state=absent).
  - When more than one instance matches, the module fails and asks for a more specific
    selection. Pass I(name) to disambiguate.
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure the internal load balancer instance of a tier is running
  ngine_io.cloudstack.internal_lb_vm:
    vpc: my-vpc
    network: web-tier
    zone: zone01
    state: started

- name: Ensure a specific internal load balancer instance is stopped
  ngine_io.cloudstack.internal_lb_vm:
    name: b-1234-VM
    zone: zone01
    state: stopped

- name: Force stop the internal load balancer instance of a tier
  ngine_io.cloudstack.internal_lb_vm:
    vpc: my-vpc
    network: web-tier
    zone: zone01
    state: stopped
    force: true
"""

RETURN = """
---
id:
  description: UUID of the internal load balancer instance.
  returned: success
  type: str
  sample: 04589590-ac63-4ffc-93f5-b698b8ac38b6
name:
  description: Name of the internal load balancer instance.
  returned: success
  type: str
  sample: b-1234-VM
state:
  description: State of the internal load balancer instance.
  returned: success
  type: str
  sample: Running
public_ip:
  description: Public IP of the internal load balancer instance.
  returned: when available
  type: str
  sample: 10.10.1.247
guest_ip_address:
  description: Guest IP of the internal load balancer instance.
  returned: when available
  type: str
  sample: 10.10.1.247
network_id:
  description: UUID of the guest network the internal load balancer instance serves.
  returned: when available
  type: str
  sample: e83f0010-4e08-493f-acc8-f5205d83b30d
vpc_id:
  description: UUID of the VPC the internal load balancer instance belongs to.
  returned: when available
  type: str
  sample: 87b1e0ce-4e01-11e4-bb66-0050569e64b8
service_offering:
  description: Name of the service offering of the internal load balancer instance.
  returned: when available
  type: str
  sample: System Offering For Software Router
template_version:
  description: Version of the system VM template.
  returned: when available
  type: str
  sample: CloudStack Release 4.20
requires_upgrade:
  description: Whether the internal load balancer instance requires an upgrade.
  returned: when available
  type: bool
  sample: false
host:
  description: Hostname of the host the internal load balancer instance is running on.
  returned: when available
  type: str
  sample: host01
created:
  description: Date of the internal load balancer instance was created.
  returned: when available
  type: str
  sample: 2026-02-08T11:26:24+0100
zone:
  description: Name of zone the internal load balancer instance is in.
  returned: success
  type: str
  sample: zone01
account:
  description: Account the internal load balancer instance is related to.
  returned: when available
  type: str
  sample: example-account
domain:
  description: Domain the internal load balancer instance is related to.
  returned: when available
  type: str
  sample: ROOT
project:
  description: Name of project the internal load balancer instance is related to.
  returned: when available
  type: str
  sample: Production
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackInternalLbVm(AnsibleCloudStack):
    """AnsibleCloudStackInternalLbVm"""

    def __init__(self, module):
        super(AnsibleCloudStackInternalLbVm, self).__init__(module)
        self.internal_lb_vm = None
        self.returns = {
            "guestipaddress": "guest_ip_address",
            "guestnetworkid": "network_id",
            "hostname": "host",
            "publicip": "public_ip",
            "requiresupgrade": "requires_upgrade",
            "serviceofferingname": "service_offering",
            "version": "template_version",
            "vpcid": "vpc_id",
        }

    def get_internal_lb_vm(self):
        if self.internal_lb_vm:
            return self.internal_lb_vm

        args = {
            "account": self.get_account(key="name"),
            "domainid": self.get_domain(key="id"),
            "projectid": self.get_project(key="id"),
            "zoneid": self.get_zone(key="id"),
            "listall": True,
            "fetch_list": True,
        }

        if self.module.params.get("vpc"):
            args["vpcid"] = self.get_vpc(key="id")

        if self.module.params.get("network"):
            args["networkid"] = self.get_network(key="id")

        internal_lb_vms = self.query_api("listInternalLoadBalancerVMs", **args) or []

        name = self.module.params.get("name")
        if name:
            internal_lb_vms = [v for v in internal_lb_vms if name.lower() in [v["name"].lower(), v["id"]]]

        if len(internal_lb_vms) > 1:
            self.fail_json(
                msg="More than one internal load balancer instance found: %s. "
                "Pass name to select one of them." % ", ".join(sorted(v["name"] for v in internal_lb_vms))
            )

        if internal_lb_vms:
            self.internal_lb_vm = internal_lb_vms[0]

        return self.internal_lb_vm

    def _get_or_fail(self):
        internal_lb_vm = self.get_internal_lb_vm()
        if not internal_lb_vm:
            self.fail_json(
                msg="Internal load balancer instance not found. It is deployed by CloudStack "
                "once the first member is assigned to an internal load balancer. Note that "
                "listInternalLoadBalancerVMs is an admin only API."
            )
        return internal_lb_vm

    def start_internal_lb_vm(self):
        internal_lb_vm = self._get_or_fail()

        if internal_lb_vm["state"].lower() != "running":
            self.result["changed"] = True
            self.result["diff"]["before"]["state"] = internal_lb_vm["state"]
            self.result["diff"]["after"]["state"] = "Running"

            if not self.module.check_mode:
                res = self.query_api("startInternalLoadBalancerVM", id=internal_lb_vm["id"])
                if self.module.params.get("poll_async"):
                    self.poll_job(res)
                    self.internal_lb_vm = None
                    internal_lb_vm = self.get_internal_lb_vm()

        return internal_lb_vm

    def stop_internal_lb_vm(self):
        internal_lb_vm = self._get_or_fail()

        if internal_lb_vm["state"].lower() != "stopped":
            self.result["changed"] = True
            self.result["diff"]["before"]["state"] = internal_lb_vm["state"]
            self.result["diff"]["after"]["state"] = "Stopped"

            if not self.module.check_mode:
                args = {
                    "id": internal_lb_vm["id"],
                    "forced": self.module.params.get("force"),
                }
                res = self.query_api("stopInternalLoadBalancerVM", **args)
                if self.module.params.get("poll_async"):
                    self.poll_job(res)
                    self.internal_lb_vm = None
                    internal_lb_vm = self.get_internal_lb_vm()

        return internal_lb_vm


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            account=dict(type="str"),
            domain=dict(type="str"),
            force=dict(type="bool", default=False),
            name=dict(type="str"),
            network=dict(type="str"),
            poll_async=dict(type="bool", default=True),
            project=dict(type="str"),
            state=dict(type="str", choices=["started", "stopped"], default="started"),
            vpc=dict(type="str"),
            zone=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_one_of=[
            ("name", "network", "vpc"),
        ],
        supports_check_mode=True,
    )

    acs_internal_lb_vm = AnsibleCloudStackInternalLbVm(module)

    state = module.params.get("state")
    if state == "stopped":
        internal_lb_vm = acs_internal_lb_vm.stop_internal_lb_vm()
    else:
        internal_lb_vm = acs_internal_lb_vm.start_internal_lb_vm()

    result = acs_internal_lb_vm.get_result(internal_lb_vm)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
