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
module: lb_internal_member
short_description: Manages internal load balancer members on Apache CloudStack based clouds.
description:
    - Add and remove instances to and from an internal load balancer created by
      M(ngine_io.cloudstack.lb_internal).
    - For public load balancer rules use M(ngine_io.cloudstack.lb_rule_member) instead.
author: Mitch Drage (@MitchDrage)
options:
  name:
    description:
      - Name of the internal load balancer the instances are assigned to.
    type: str
    required: true
  network:
    description:
      - Name of the VPC tier the internal load balancer balances traffic to.
    type: str
    required: true
  vms:
    description:
      - List of instance names the internal load balancer balances traffic to.
    type: list
    elements: str
    required: true
    aliases: [ vm ]
  vpc:
    description:
      - Name of the VPC the I(network) belongs to.
    type: str
  zone:
    description:
      - Name of the zone the internal load balancer belongs to.
    type: str
    required: true
  domain:
    description:
      - Domain the internal load balancer is related to.
    type: str
  account:
    description:
      - Account the internal load balancer is related to.
    type: str
  project:
    description:
      - Name of the project the internal load balancer is related to.
    type: str
  state:
    description:
      - Whether the instances should be assigned to or removed from the internal load balancer.
    type: str
    default: present
    choices: [ present, absent ]
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: true
notes:
  - The instances must be members of the same VPC tier the internal load balancer balances
    traffic to.
  - The C(InternalLbVm) system instance is only deployed by CloudStack once the first member
    has been assigned. It can be managed using M(ngine_io.cloudstack.internal_lb_vm).
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure instances are assigned to the internal load balancer
  ngine_io.cloudstack.lb_internal_member:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
    vms:
      - web-01
      - web-02

- name: Ensure an instance is removed from the internal load balancer
  ngine_io.cloudstack.lb_internal_member:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
    vm: web-02
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the internal load balancer.
  returned: success
  type: str
  sample: a5396f25-945f-4968-854e-8400af7bee97
name:
  description: Name of the internal load balancer.
  returned: success
  type: str
  sample: web-ilb
algorithm:
  description: Load balancing algorithm used.
  returned: success
  type: str
  sample: roundrobin
source_port:
  description: Source port the internal load balancer listens on.
  returned: success
  type: int
  sample: 80
instance_port:
  description: Port on the balanced instances traffic is forwarded to.
  returned: success
  type: int
  sample: 8080
source_ip:
  description: Source IP address of the internal load balancer.
  returned: success
  type: str
  sample: 10.10.1.247
network_id:
  description: UUID of the network the internal load balancer balances traffic to.
  returned: success
  type: str
  sample: e83f0010-4e08-493f-acc8-f5205d83b30d
vms:
  description: List of instance names assigned to the internal load balancer.
  returned: success
  type: list
  sample: [ web-01, web-02 ]
zone:
  description: Name of the zone the internal load balancer belongs to.
  returned: success
  type: str
  sample: zone01
account:
  description: Account the internal load balancer is related to.
  returned: when available
  type: str
  sample: example-account
domain:
  description: Domain the internal load balancer is related to.
  returned: when available
  type: str
  sample: ROOT
project:
  description: Name of the project the internal load balancer is related to.
  returned: when available
  type: str
  sample: Production
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together

LB_SCHEME = "Internal"


class AnsibleCloudStackLbInternalMember(AnsibleCloudStack):
    """AnsibleCloudStackLbInternalMember"""

    def __init__(self, module):
        super(AnsibleCloudStackLbInternalMember, self).__init__(module)
        self.lb_internal = None
        self.vms = None
        self.returns = {
            "algorithm": "algorithm",
            "networkid": "network_id",
            "sourceipaddress": "source_ip",
            "sourceipaddressnetworkid": "source_ip_network_id",
        }
        self.returns_to_int = {
            "instanceport": "instance_port",
            "sourceport": "source_port",
        }

    def _get_common_args(self):
        args = {
            "account": self.get_account(key="name"),
            "domainid": self.get_domain(key="id"),
            "name": self.module.params.get("name"),
            "networkid": self.get_network(key="id"),
            "projectid": self.get_project(key="id"),
        }
        return args

    def get_lb_internal(self):
        if self.lb_internal:
            return self.lb_internal

        args = self._get_common_args()
        args["scheme"] = LB_SCHEME
        args["fetch_list"] = True

        # listLoadBalancers only returns rules with display=true unless fordisplay is passed
        # explicitly, see ListApplicationLoadBalancersCmd.getDisplay(). Without the second
        # pass, a load balancer created with for_display=false would not be found here.
        for fordisplay in (None, False):
            if fordisplay is None:
                args.pop("fordisplay", None)
            else:
                args["fordisplay"] = fordisplay

            lb_internals = self.query_api("listLoadBalancers", **args)
            if lb_internals:
                for lb_internal in lb_internals:
                    if lb_internal["name"] == self.module.params.get("name"):
                        self.lb_internal = lb_internal
                        return self.lb_internal

        return None

    def _get_vms(self):
        """Return the instances of the load balanced network."""
        if self.vms is None:
            args = {
                "account": self.get_account(key="name"),
                "domainid": self.get_domain(key="id"),
                "networkid": self.get_network(key="id"),
                "projectid": self.get_project(key="id"),
                "fetch_list": True,
            }
            self.vms = self.query_api("listVirtualMachines", **args) or []
        return self.vms

    def _get_member_ids(self, lb_internal):
        """Return the UUIDs of the instances assigned to the load balancer.

        Matching is done on UUID, never on name: loadbalancerinstance[] reports the internal
        instance name (i-2-10-QA), not the name the user deployed the instance with.
        """
        return set(vm["id"] for vm in lb_internal.get("loadbalancerinstance") or [])

    def _get_member_names(self, lb_internal):
        """Return the user facing names of the instances assigned to the load balancer."""
        member_ids = self._get_member_ids(lb_internal)
        names = []
        for vm in self._get_vms():
            if vm["id"] in member_ids:
                names.append(vm["name"])
        return sorted(names)

    def _ensure_members(self, operation):
        lb_internal = self.get_lb_internal()
        if not lb_internal:
            self.fail_json(msg="Internal load balancer not found: %s" % self.module.params.get("name"))

        # Resolve the wanted instances to UUIDs. Only instances of the load balanced network
        # can be assigned, so a name not found here would fail in the API anyway.
        by_name = dict()
        for vm in self._get_vms():
            by_name[vm["name"]] = vm["id"]
            by_name[vm["id"]] = vm["id"]

        wanted_ids = []
        for name in self.module.params.get("vms"):
            if name not in by_name:
                self.fail_json(msg="Instance not found in network %s: %s" % (self.module.params.get("network"), name))
            wanted_ids.append(by_name[name])

        existing_ids = self._get_member_ids(lb_internal)

        if operation == "add":
            api = "assignToLoadBalancerRule"
            to_change_ids = [i for i in wanted_ids if i not in existing_ids]
            after_ids = existing_ids | set(wanted_ids)
        else:
            api = "removeFromLoadBalancerRule"
            to_change_ids = [i for i in wanted_ids if i in existing_ids]
            after_ids = existing_ids - set(wanted_ids)

        if not to_change_ids:
            return lb_internal

        id_to_name = dict((vm["id"], vm["name"]) for vm in self._get_vms())
        self.result["changed"] = True
        self.result["diff"]["before"]["vms"] = sorted(id_to_name.get(i, i) for i in existing_ids)
        self.result["diff"]["after"]["vms"] = sorted(id_to_name.get(i, i) for i in after_ids)

        if not self.module.check_mode:
            res = self.query_api(api, id=lb_internal["id"], virtualmachineids=to_change_ids)
            if self.module.params.get("poll_async"):
                self.poll_job(res)
                # Re-read so the returned members reflect the change.
                self.lb_internal = None
                lb_internal = self.get_lb_internal()

        return lb_internal

    def add_members(self):
        return self._ensure_members("add")

    def remove_members(self):
        return self._ensure_members("remove")

    def get_result(self, resource):
        if resource:
            lb_rules = resource.get("loadbalancerrule") or []
            if lb_rules:
                resource = dict(resource)
                resource["sourceport"] = lb_rules[0].get("sourceport")
                resource["instanceport"] = lb_rules[0].get("instanceport")
                resource["state"] = lb_rules[0].get("state")

        super(AnsibleCloudStackLbInternalMember, self).get_result(resource)

        if resource:
            self.result["vms"] = self._get_member_names(resource)
        return self.result


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            account=dict(type="str"),
            domain=dict(type="str"),
            name=dict(type="str", required=True),
            network=dict(type="str", required=True),
            poll_async=dict(type="bool", default=True),
            project=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            vms=dict(type="list", elements="str", required=True, aliases=["vm"]),
            vpc=dict(type="str"),
            zone=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        supports_check_mode=True,
    )

    acs_lb_internal_member = AnsibleCloudStackLbInternalMember(module)

    state = module.params.get("state")
    if state == "absent":
        lb_internal = acs_lb_internal_member.remove_members()
    else:
        lb_internal = acs_lb_internal_member.add_members()

    result = acs_lb_internal_member.get_result(lb_internal)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
