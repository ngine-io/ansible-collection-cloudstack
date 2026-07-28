#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: pod_info
short_description: Gathering information about pods from Apache CloudStack based clouds.
description:
  - Gathering information from the API of a pod.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  name:
    description:
      - Name of the pod.
      - If not specified, information about all pods is gathered.
    type: str
  zone:
    description:
      - Name of the zone in which the pod belongs to.
    type: str
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Gather information from a pod
  ngine_io.cloudstack.pod_info:
    name: pod1
    zone: ch-zrh-ix-01
  register: pod

- name: Show the returned results of the registered variable
  debug:
    msg: "{{ pod }}"

- name: Gather information from all pods
  ngine_io.cloudstack.pod_info:
  register: pods
"""

RETURN = """
---
pods:
  description: A list of matching pods.
  type: list
  returned: success
  contains:
    id:
      description: UUID of the pod.
      returned: success
      type: str
      sample: 04589590-ac63-4ffc-93f5-b698b8ac38b6
    name:
      description: Name of the pod.
      returned: success
      type: str
      sample: pod01
    start_ip:
      description: Starting IP of the pod.
      returned: success
      type: str
      sample: 10.100.1.101
    end_ip:
      description: Ending IP of the pod.
      returned: success
      type: str
      sample: 10.100.1.254
    netmask:
      description: Netmask of the pod.
      returned: success
      type: str
      sample: 255.255.255.0
    gateway:
      description: Gateway of the pod.
      returned: success
      type: str
      sample: 10.100.1.1
    allocation_state:
      description: State of the pod.
      returned: success
      type: str
      sample: Enabled
    zone:
      description: Name of zone the pod is in.
      returned: success
      type: str
      sample: ch-gva-2
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec


class AnsibleCloudStackPodInfo(AnsibleCloudStack):
    """AnsibleCloudStackPodInfo"""

    def __init__(self, module):
        super(AnsibleCloudStackPodInfo, self).__init__(module)
        self.returns = {
            "endip": "end_ip",
            "startip": "start_ip",
            "gateway": "gateway",
            "netmask": "netmask",
            "allocationstate": "allocation_state",
            "zonename": "zone",
        }

    def _transform_ip_list(self, resource):
        """Workaround for 4.11 return API break"""
        keys = ["endip", "startip"]
        if resource:
            for key in keys:
                if key in resource and isinstance(resource[key], list):
                    resource[key] = resource[key][0]
        return resource

    def get_pod(self):
        args = {}
        if self.module.params.get("zone"):
            args["zoneid"] = self.get_zone(key="id")
        if self.module.params.get("name"):
            args["name"] = self.module.params.get("name")

        pods = self.query_api("listPods", **args)
        if pods:
            pods = pods["pod"]
        else:
            pods = []
        return {"pods": [self.update_result(self._transform_ip_list(resource)) for resource in pods]}


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str"),
            zone=dict(type="str"),
        )
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    apod_info = AnsibleCloudStackPodInfo(module=module)
    result = apod_info.get_pod()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
