#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: instance_nic_secondaryip
short_description: Manages secondary IPs of an instance on Apache CloudStack based clouds.
description:
    - Add and remove secondary IPs to and from a NIC of an instance.
author: René Moser (@resmo)
version_added: 0.1.0
options:
  vm:
    description:
      - Name of instance.
    type: str
    required: true
    aliases: [ name ]
  network:
    description:
      - Name of the network.
      - Required to find the NIC if instance has multiple networks assigned.
    type: str
  vm_guest_ip:
    description:
      - Secondary IP address to be added to the instance nic.
      - If not set, the API always returns a new IP address and idempotency is not given.
    type: str
    aliases: [ secondary_ip ]
  vpc:
    description:
      - Name of the VPC the I(vm) is related to.
    type: str
  domain:
    description:
      - Domain the instance is related to.
    type: str
  account:
    description:
      - Account the instance is related to.
    type: str
  project:
    description:
      - Name of the project the instance is deployed in.
    type: str
  zone:
    description:
      - Name of the zone in which the instance is deployed in.
    type: str
    required: true
  state:
    description:
      - State of the ipaddress.
    type: str
    default: present
    choices: [ present, absent ]
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: yes
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Assign a specific IP to the default NIC of the VM
  ngine_io.cloudstack.instance_nic_secondaryip:
    vm: customer_xy
    zone: zone01
    vm_guest_ip: 10.10.10.10

# Note: If vm_guest_ip is not set, you will get a new IP address on every run.
- name: Assign an IP to the default NIC of the VM
  ngine_io.cloudstack.instance_nic_secondaryip:
    vm: customer_xy
    zone: zone01

- name: Remove a specific IP from the default NIC
  ngine_io.cloudstack.instance_nic_secondaryip:
    vm: customer_xy
    zone: zone01
    vm_guest_ip: 10.10.10.10
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the NIC.
  returned: success
  type: str
  sample: 87b1e0ce-4e01-11e4-bb66-0050569e64b8
vm:
  description: Name of the VM.
  returned: success
  type: str
  sample: web-01
ip_address:
  description: Primary IP of the NIC.
  returned: success
  type: str
  sample: 10.10.10.10
netmask:
  description: Netmask of the NIC.
  returned: success
  type: str
  sample: 255.255.255.0
mac_address:
  description: MAC address of the NIC.
  returned: success
  type: str
  sample: 02:00:33:31:00:e4
vm_guest_ip:
  description: Secondary IP of the NIC.
  returned: success
  type: str
  sample: 10.10.10.10
network:
  description: Name of the network if not default.
  returned: success
  type: str
  sample: sync network
domain:
  description: Domain the VM is related to.
  returned: success
  type: str
  sample: example domain
account:
  description: Account the VM is related to.
  returned: success
  type: str
  sample: example account
project:
  description: Name of project the VM is related to.
  returned: success
  type: str
  sample: Production
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackInstanceNicSecondaryIp(AnsibleCloudStack):
    """AnsibleCloudStackInstanceNicSecondaryIp"""

    def __init__(self, module):
        super(AnsibleCloudStackInstanceNicSecondaryIp, self).__init__(module)
        self.vm_guest_ip = self.module.params.get("vm_guest_ip")
        self.nic = None
        self.returns = {
            "ipaddress": "ip_address",
            "macaddress": "mac_address",
            "netmask": "netmask",
        }

    def get_nic(self):
        if self.nic:
            return self.nic
        args = {
            "virtualmachineid": self.get_vm(key="id"),
            "networkid": self.get_network(key="id"),
        }
        nics = self.query_api("listNics", **args)
        if nics:
            self.nic = nics["nic"][0]
            return self.nic
        self.fail_json(msg="NIC for VM %s in network %s not found" % (self.get_vm(key="name"), self.get_network(key="name")))

    def get_secondary_ip(self):
        nic = self.get_nic()
        if self.vm_guest_ip:
            secondary_ips = nic.get("secondaryip") or [] if nic is not None else []
            for secondary_ip in secondary_ips:
                if secondary_ip["ipaddress"] == self.vm_guest_ip:
                    return secondary_ip
        return None

    def present_nic_ip(self):
        nic = self.get_nic()
        if not self.get_secondary_ip():
            self.result["changed"] = True
            args = {
                "nicid": nic["id"] if nic is not None else "",
                "ipaddress": self.vm_guest_ip,
            }

            if not self.module.check_mode:
                res = self.query_api("addIpToNic", **args)

                poll_async = self.module.params.get("poll_async")
                if poll_async:
                    nic = self.poll_job(res, "nicsecondaryip")
                    # Save result for RETURNS
                    self.vm_guest_ip = nic["ipaddress"] if nic is not None else ""
        return nic

    def absent_nic_ip(self):
        nic = self.get_nic()
        secondary_ip = self.get_secondary_ip()
        if secondary_ip:
            self.result["changed"] = True
            if not self.module.check_mode:
                res = self.query_api("removeIpFromNic", id=secondary_ip["id"])

                poll_async = self.module.params.get("poll_async")
                if poll_async:
                    self.poll_job(res, "nicsecondaryip")
        return nic

    def get_result(self, resource):
        super(AnsibleCloudStackInstanceNicSecondaryIp, self).get_result(resource)
        if resource and not self.module.params.get("network"):
            self.module.params["network"] = resource.get("networkid")
        self.result["network"] = self.get_network(key="name")
        self.result["vm"] = self.get_vm(key="name")
        self.result["vm_guest_ip"] = self.vm_guest_ip
        return self.result


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            vm=dict(type="str", required=True, aliases=["name"]),
            vm_guest_ip=dict(type="str", aliases=["secondary_ip"]),
            network=dict(type="str"),
            vpc=dict(type="str"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
            domain=dict(type="str"),
            account=dict(type="str"),
            project=dict(type="str"),
            zone=dict(type="str", required=True),
            poll_async=dict(type="bool", default=True),
        )  # type: ignore
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        supports_check_mode=True,
        required_if=(
            [
                ("state", "absent", ["vm_guest_ip"]),
            ]
        ),
    )

    ainstance_nic_secondaryip = AnsibleCloudStackInstanceNicSecondaryIp(module)
    state = module.params.get("state")

    if state == "absent":
        nic = ainstance_nic_secondaryip.absent_nic_ip()
    else:
        nic = ainstance_nic_secondaryip.present_nic_ip()

    result = ainstance_nic_secondaryip.get_result(nic)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
