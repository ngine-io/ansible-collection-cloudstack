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
module: lb_internal
short_description: Manages internal load balancers on Apache CloudStack based clouds.
description:
    - Create and remove internal (application) load balancers on a VPC tier.
    - Internal load balancers use a different API family than M(ngine_io.cloudstack.lb_rule),
      which manages public load balancer rules only and can not see or manage internal ones.
    - Existing internal load balancers are matched by name within the network scope.
    - Only I(for_display) can be changed after creation. See the notes below.
author: Mitch Drage (@MitchDrage)
options:
  name:
    description:
      - Name of the internal load balancer.
    type: str
    required: true
  network:
    description:
      - Name of the VPC tier the internal load balancer balances traffic to.
      - The network offering of this tier must support the LB service with the
        C(InternalLbVm) provider.
    type: str
    required: true
  source_port:
    description:
      - Source port the internal load balancer listens on.
      - Required on I(state=present).
      - Can not be changed after creation.
    type: int
  instance_port:
    description:
      - Port on the balanced instances traffic is forwarded to.
      - Required on I(state=present).
      - Can not be changed after creation.
    type: int
  algorithm:
    description:
      - Load balancing algorithm.
      - Defaults to C(source) when the load balancer is created.
      - When not given, the algorithm of an existing load balancer is left as it is.
      - Can not be changed after creation.
    type: str
    choices: [ source, roundrobin, leastconn ]
  source_ip:
    description:
      - Source IP address of the internal load balancer.
      - Automatically allocated from I(source_ip_network) when not given.
      - On I(force=true), the address of the existing load balancer is kept when not given.
      - Can not be changed after creation.
    type: str
  source_ip_network:
    description:
      - Name of the network the source IP address is taken from.
      - Defaults to I(network) when not given.
      - Can not be changed after creation.
    type: str
  description:
    description:
      - Description of the internal load balancer.
      - Only used on creation, see the notes below.
    type: str
  for_display:
    description:
      - Whether the internal load balancer is displayed to the regular user.
      - Requires an admin account to be idempotent, see the notes below.
    type: bool
  force:
    description:
      - Whether to delete and recreate the internal load balancer when an option which can not
        be updated differs from the existing one.
      - Without it, such a difference fails the task instead.
      - Only considered on I(state=present). See the notes below for the consequences.
    type: bool
    default: false
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
      - State of the internal load balancer.
    type: str
    default: present
    choices: [ present, absent ]
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: true
notes:
  - The CloudStack API only allows I(for_display) to be updated on an existing internal
    load balancer. When any other option differs, this module fails and names the differing
    options, so a live load balancer is never torn down by an unrelated playbook run. Set
    I(force=true) to delete and recreate it instead, or use I(state=absent) followed by
    I(state=present).
  - I(force=true) only acts when an option actually differs, so it stays idempotent and can
    safely be driven by a playbook variable.
  - Recreating drops every member assigned to the load balancer. Re-apply them with
    M(ngine_io.cloudstack.lb_internal_member) afterwards.
  - Recreating keeps the source IP address of the existing load balancer, so the address
    stays stable across a recreate. Give I(source_ip) to move it to a different address.
  - The API returns C(fordisplay) to admin accounts only. When running as a regular user,
    this module can not detect drift on I(for_display) and will emit a warning instead of
    updating it. I(for_display) is always applied on creation.
  - The API does not return I(description) at all, so it can neither be verified nor changed
    after creation.
  - Members are managed separately and are not in the scope of this module. They can be
    assigned using the C(assignToLoadBalancerRule) API.
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure an internal load balancer is present
  ngine_io.cloudstack.lb_internal:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
    source_port: 80
    instance_port: 8080
    algorithm: roundrobin

- name: Ensure an internal load balancer with a fixed source IP
  ngine_io.cloudstack.lb_internal:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
    source_port: 80
    instance_port: 8080
    source_ip: 10.10.1.100

- name: Ensure an internal load balancer, recreating it if an immutable option changed
  ngine_io.cloudstack.lb_internal:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
    source_port: 8080
    instance_port: 8080
    force: true

- name: Ensure an internal load balancer is absent
  ngine_io.cloudstack.lb_internal:
    name: web-ilb
    vpc: my-vpc
    network: web-tier
    zone: zone01
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
source_ip_network_id:
  description: UUID of the network the source IP address is taken from.
  returned: success
  type: str
  sample: e83f0010-4e08-493f-acc8-f5205d83b30d
network_id:
  description: UUID of the network the internal load balancer balances traffic to.
  returned: success
  type: str
  sample: e83f0010-4e08-493f-acc8-f5205d83b30d
network:
  description: Name of the network the internal load balancer balances traffic to.
  returned: success
  type: str
  sample: web-tier
for_display:
  description: Whether the internal load balancer is displayed to the regular user.
  returned: when running as an admin account
  type: bool
  sample: true
state:
  description: State of the internal load balancer rule.
  returned: success
  type: str
  sample: Active
zone:
  description: Name of the zone the internal load balancer belongs to.
  returned: success
  type: str
  sample: zone01
project:
  description: Name of the project the internal load balancer is related to.
  returned: when available
  type: str
  sample: Production
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
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together

# The API only accepts this scheme, see CreateApplicationLoadBalancerCmd. It is deliberately
# not exposed as an option, as that would imply a Public option the API rejects.
LB_SCHEME = "Internal"

# Applied on creation only, see _create_lb_internal().
LB_DEFAULT_ALGORITHM = "source"


class AnsibleCloudStackLbInternal(AnsibleCloudStack):
    """AnsibleCloudStackLbInternal"""

    def __init__(self, module):
        super(AnsibleCloudStackLbInternal, self).__init__(module)
        self.lb_internal = None
        self.source_ip_network = None
        self.returns = {
            "algorithm": "algorithm",
            "fordisplay": "for_display",
            "networkid": "network_id",
            "sourceipaddress": "source_ip",
            "sourceipaddressnetworkid": "source_ip_network_id",
        }
        self.returns_to_int = {
            "instanceport": "instance_port",
            "sourceport": "source_port",
        }

    def get_source_ip_network(self, key=None):
        """Return the network the source IP is taken from, defaults to the LB network."""
        source_ip_network = self.module.params.get("source_ip_network")
        if not source_ip_network:
            return self.get_network(key=key)

        if self.source_ip_network:
            return self._get_by_key(key, self.source_ip_network)

        args = {
            "account": self.get_account(key="name"),
            "domainid": self.get_domain(key="id"),
            "projectid": self.get_project(key="id"),
            "vpcid": self.get_vpc(key="id"),
            "zoneid": self.get_zone(key="id"),
            "fetch_list": True,
        }
        networks = self.query_api("listNetworks", **args)
        if networks:
            for n in networks:
                if source_ip_network in [n["displaytext"], n["name"], n["id"]]:
                    self.source_ip_network = n
                    return self._get_by_key(key, self.source_ip_network)
        self.fail_json(msg="Network '%s' not found" % source_ip_network)

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
        # The response carries no scheme, so it must be filtered on the query. This also
        # ensures a public LB rule of the same name is never matched.
        args["scheme"] = LB_SCHEME
        args["fetch_list"] = True

        # listLoadBalancers only returns rules with display=true unless fordisplay is passed
        # explicitly: ListApplicationLoadBalancersCmd.getDisplay() falls back to a hardcoded
        # true in BaseListAccountResourcesCmd, which searchForLoadBalancers then applies as a
        # search parameter. Without the second pass, a load balancer created with
        # for_display=false would be invisible here and we would create a duplicate.
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

    def _get_lb_rule(self, lb_internal):
        """Return the first LB rule, which carries the ports."""
        lb_rules = lb_internal.get("loadbalancerrule") or []
        return lb_rules[0] if lb_rules else {}

    def _get_immutable_diff(self, lb_internal):
        """Return a list of (option, current, wanted) for options which can not be updated."""
        lb_rule = self._get_lb_rule(lb_internal)

        # (module option, wanted value, current value)
        candidates = [
            ("source_port", self.module.params.get("source_port"), lb_rule.get("sourceport")),
            ("instance_port", self.module.params.get("instance_port"), lb_rule.get("instanceport")),
            ("algorithm", self.module.params.get("algorithm"), lb_internal.get("algorithm")),
            ("source_ip", self.module.params.get("source_ip"), lb_internal.get("sourceipaddress")),
            (
                "source_ip_network",
                self.get_source_ip_network(key="id") if self.module.params.get("source_ip_network") else None,
                lb_internal.get("sourceipaddressnetworkid"),
            ),
        ]

        diff = []
        for option, wanted, current in candidates:
            # Not given, nothing to compare against. Ports are enforced by required_if.
            if wanted is None:
                continue

            if isinstance(wanted, int):
                differs = current is None or int(current) != wanted
            else:
                differs = str(current).lower() != str(wanted).lower()

            if differs:
                diff.append((option, current, wanted))

        return diff

    def _update_for_display(self, lb_internal):
        for_display = self.module.params.get("for_display")
        if for_display is None:
            return lb_internal

        # fordisplay is returned to admin accounts only, so drift can not be detected as a
        # regular user. Warn rather than updating on every run.
        if "fordisplay" not in lb_internal:
            self.module.warn(
                "Can not verify for_display: the API returns it to admin accounts only. "
                "Leaving it unchanged on internal load balancer '%s'." % lb_internal["name"]
            )
            return lb_internal

        if lb_internal["fordisplay"] == for_display:
            return lb_internal

        self.result["changed"] = True
        self.result["diff"]["before"]["for_display"] = lb_internal["fordisplay"]
        self.result["diff"]["after"]["for_display"] = for_display

        if not self.module.check_mode:
            args = {
                "id": lb_internal["id"],
                "fordisplay": for_display,
            }
            res = self.query_api("updateLoadBalancer", **args)
            if self.module.params.get("poll_async"):
                lb_internal = self.poll_job(res, "loadbalancer")

        return lb_internal

    def _create_lb_internal(self, source_ip=None):
        args = self._get_common_args()
        args.update(
            {
                # The default is applied here rather than in the argument spec: a spec level
                # default is indistinguishable from a value the user asked for, and would make
                # an omitted algorithm look like drift on an existing load balancer.
                "algorithm": self.module.params.get("algorithm") or LB_DEFAULT_ALGORITHM,
                "description": self.module.params.get("description"),
                "fordisplay": self.module.params.get("for_display"),
                "instanceport": self.module.params.get("instance_port"),
                "scheme": LB_SCHEME,
                "sourceipaddress": self.module.params.get("source_ip") or source_ip,
                "sourceipaddressnetworkid": self.get_source_ip_network(key="id"),
                "sourceport": self.module.params.get("source_port"),
            }
        )

        lb_internal = None
        if not self.module.check_mode:
            res = self.query_api("createLoadBalancer", **args)
            if self.module.params.get("poll_async"):
                lb_internal = self.poll_job(res, "loadbalancer")
        return lb_internal

    def _recreate_lb_internal(self, lb_internal, diff):
        """Delete and recreate, the only way to change an option the API treats as immutable."""
        self.result["changed"] = True
        for option, current, wanted in diff:
            self.result["diff"]["before"][option] = current
            self.result["diff"]["after"][option] = wanted

        if self.module.check_mode:
            return lb_internal

        # Keep the address the load balancer already has, so consumers pointing at the VIP
        # keep working across the recreate. An explicit source_ip still wins.
        source_ip = lb_internal.get("sourceipaddress")

        res = self.query_api("deleteLoadBalancer", id=lb_internal["id"])
        if self.module.params.get("poll_async"):
            self.poll_job(res)

        self.lb_internal = None
        return self._create_lb_internal(source_ip=source_ip)

    def present_lb_internal(self):
        lb_internal = self.get_lb_internal()

        if lb_internal:
            diff = self._get_immutable_diff(lb_internal)
            if not diff:
                lb_internal = self._update_for_display(lb_internal)
            elif self.module.params.get("force"):
                lb_internal = self._recreate_lb_internal(lb_internal, diff)
            else:
                self.fail_json(
                    msg="Internal load balancer '%s' exists but the following options can not be "
                    "changed: %s. Use force=true to delete and recreate it, or state=absent "
                    "followed by state=present."
                    % (
                        self.module.params.get("name"),
                        ", ".join("%s (current: %s, wanted: %s)" % d for d in diff),
                    )
                )
        else:
            self.result["changed"] = True
            lb_internal = self._create_lb_internal()

        self.lb_internal = lb_internal
        return lb_internal

    def absent_lb_internal(self):
        lb_internal = self.get_lb_internal()
        if lb_internal:
            self.result["changed"] = True
            if not self.module.check_mode:
                res = self.query_api("deleteLoadBalancer", id=lb_internal["id"])
                if self.module.params.get("poll_async"):
                    self.poll_job(res)
        return lb_internal

    def get_result(self, resource):
        if resource:
            # The ports live inside loadbalancerrule[], lift them so they can be returned.
            lb_rule = self._get_lb_rule(resource)
            if lb_rule:
                resource = dict(resource)
                resource["sourceport"] = lb_rule.get("sourceport")
                resource["instanceport"] = lb_rule.get("instanceport")
                resource["state"] = lb_rule.get("state")
        return super(AnsibleCloudStackLbInternal, self).get_result(resource)


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            account=dict(type="str"),
            algorithm=dict(type="str", choices=["source", "roundrobin", "leastconn"]),
            description=dict(type="str"),
            domain=dict(type="str"),
            for_display=dict(type="bool"),
            force=dict(type="bool", default=False),
            instance_port=dict(type="int"),
            name=dict(type="str", required=True),
            network=dict(type="str", required=True),
            poll_async=dict(type="bool", default=True),
            project=dict(type="str"),
            source_ip=dict(type="str"),
            source_ip_network=dict(type="str"),
            source_port=dict(type="int"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            vpc=dict(type="str"),
            zone=dict(type="str", required=True),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "present", ["source_port", "instance_port"]),
        ],
        supports_check_mode=True,
    )

    acs_lb_internal = AnsibleCloudStackLbInternal(module)

    state = module.params.get("state")
    if state == "absent":
        lb_internal = acs_lb_internal.absent_lb_internal()
    else:
        lb_internal = acs_lb_internal.present_lb_internal()

    result = acs_lb_internal.get_result(lb_internal)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
