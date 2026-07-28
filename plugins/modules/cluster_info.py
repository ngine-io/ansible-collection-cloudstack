#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: cluster_info
short_description: Gathering information about clusters from Apache CloudStack based clouds.
description:
  - Gathering information from the API of a cluster.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  name:
    description:
      - Name of the cluster.
      - If not specified, information about all clusters is gathered.
    type: str
  zone:
    description:
      - Name of the zone in which the cluster belongs to.
    type: str
  pod:
    description:
      - Name of the pod in which the cluster belongs to.
    type: str
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Gather information from a cluster
  ngine_io.cloudstack.cluster_info:
    name: kvm-cluster-01
    zone: ch-zrh-ix-01
  register: cluster

- name: Show the returned results of the registered variable
  debug:
    msg: "{{ cluster }}"

- name: Gather information from all clusters
  ngine_io.cloudstack.cluster_info:
  register: clusters
"""

RETURN = """
---
clusters:
  description: A list of matching clusters.
  type: list
  returned: success
  contains:
    id:
      description: UUID of the cluster.
      returned: success
      type: str
      sample: 04589590-ac63-4ffc-93f5-b698b8ac38b6
    name:
      description: Name of the cluster.
      returned: success
      type: str
      sample: cluster01
    allocation_state:
      description: State of the cluster.
      returned: success
      type: str
      sample: Enabled
    cluster_type:
      description: Type of the cluster.
      returned: success
      type: str
      sample: ExternalManaged
    cpu_overcommit_ratio:
      description: The CPU overcommit ratio of the cluster.
      returned: success
      type: str
      sample: 1.0
    memory_overcommit_ratio:
      description: The memory overcommit ratio of the cluster.
      returned: success
      type: str
      sample: 1.0
    managed_state:
      description: Whether this cluster is managed by CloudStack.
      returned: success
      type: str
      sample: Managed
    ovm3_vip:
      description: Ovm3 VIP to use for pooling and/or clustering
      returned: success
      type: str
      sample: 10.10.10.101
    hypervisor:
      description: Hypervisor of the cluster.
      returned: success
      type: str
      sample: VMware
    zone:
      description: Name of zone the cluster is in.
      returned: success
      type: str
      sample: ch-gva-2
    pod:
      description: Name of pod the cluster is in.
      returned: success
      type: str
      sample: pod01
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec


class AnsibleCloudStackClusterInfo(AnsibleCloudStack):
    """AnsibleCloudStackClusterInfo"""

    def __init__(self, module):
        super(AnsibleCloudStackClusterInfo, self).__init__(module)
        self.returns = {
            "allocationstate": "allocation_state",
            "hypervisortype": "hypervisor",
            "clustertype": "cluster_type",
            "podname": "pod",
            "managedstate": "managed_state",
            "memoryovercommitratio": "memory_overcommit_ratio",
            "cpuovercommitratio": "cpu_overcommit_ratio",
            "ovm3vip": "ovm3_vip",
            "zonename": "zone",
        }

    def get_cluster(self):
        args = {}
        if self.module.params.get("zone"):
            args["zoneid"] = self.get_zone(key="id")
        if self.module.params.get("pod"):
            args["podid"] = self.get_pod(key="id")
        if self.module.params.get("name"):
            args["name"] = self.module.params.get("name")

        clusters = self.query_api("listClusters", **args)
        if clusters:
            clusters = clusters["cluster"]
        else:
            clusters = []
        return {"clusters": [self.update_result(resource) for resource in clusters]}


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str"),
            zone=dict(type="str"),
            pod=dict(type="str"),
        )
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    acluster_info = AnsibleCloudStackClusterInfo(module=module)
    result = acluster_info.get_cluster()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
