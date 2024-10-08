#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: configuration
short_description: Manages configuration on Apache CloudStack based clouds.
description:
    - Manages global, zone, account, storage and cluster configurations.
author: René Moser (@resmo)
version_added: 0.1.0
options:
  name:
    description:
      - Name of the configuration.
    type: str
    required: true
  value:
    description:
      - Value of the configuration.
    type: str
    required: true
  account:
    description:
      - Ensure the value for corresponding account.
    type: str
  domain:
    description:
      - Domain the account is related to.
      - Only considered if I(account) is used.
    type: str
    default: ROOT
  zone:
    description:
      - Ensure the value for corresponding zone.
    type: str
  storage:
    description:
      - Ensure the value for corresponding storage pool.
    type: str
  cluster:
    description:
      - Ensure the value for corresponding cluster.
    type: str
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure global configuration
  ngine_io.cloudstack.configuration:
    name: router.reboot.when.outofband.migrated
    value: false

- name: Ensure zone configuration
  ngine_io.cloudstack.configuration:
    name: router.reboot.when.outofband.migrated
    zone: ch-gva-01
    value: true

- name: Ensure storage configuration
  ngine_io.cloudstack.configuration:
    name: storage.overprovisioning.factor
    storage: storage01
    value: 2.0

- name: Ensure account configuration
  ngine_io.cloudstack.configuration:
    name: allow.public.user.templates
    value: false
    account: acme inc
    domain: customers
"""

RETURN = """
---
category:
  description: Category of the configuration.
  returned: success
  type: str
  sample: Advanced
scope:
  description: Scope (zone/cluster/storagepool/account) of the parameter that needs to be updated.
  returned: success
  type: str
  sample: storagepool
description:
  description: Description of the configuration.
  returned: success
  type: str
  sample: Setup the host to do multipath
name:
  description: Name of the configuration.
  returned: success
  type: str
  sample: zone.vlan.capacity.notificationthreshold
value:
  description: Value of the configuration.
  returned: success
  type: str
  sample: "0.75"
account:
  description: Account of the configuration.
  returned: success
  type: str
  sample: admin
Domain:
  description: Domain of account of the configuration.
  returned: success
  type: str
  sample: ROOT
zone:
  description: Zone of the configuration.
  returned: success
  type: str
  sample: ch-gva-01
cluster:
  description: Cluster of the configuration.
  returned: success
  type: str
  sample: cluster01
storage:
  description: Storage of the configuration.
  returned: success
  type: str
  sample: storage01
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackConfiguration(AnsibleCloudStack):
    """AnsibleCloudStackConfiguration"""

    def __init__(self, module):
        super(AnsibleCloudStackConfiguration, self).__init__(module)
        self.returns = {
            "category": "category",
            "scope": "scope",
            "value": "value",
        }
        self.storage = None
        self.account = None
        self.cluster = None

    def _get_common_configuration_args(self):
        args = {
            "name": self.module.params.get("name"),
            "accountid": self.get_account(key="id"),
            "storageid": self.get_storage(key="id"),
            "zoneid": self.get_zone(key="id"),
            "clusterid": self.get_cluster(key="id"),
        }
        return args

    def get_zone(self, key=None):
        # zone is optional as it means that the configuration is aimed at a global setting.
        zone = self.module.params.get("zone")
        if zone:
            return super(AnsibleCloudStackConfiguration, self).get_zone(key=key)

    def get_cluster(self, key=None):
        if not self.cluster:
            cluster_name = self.module.params.get("cluster")
            if not cluster_name:
                return None
            args = {
                "name": cluster_name,
            }
            clusters = self.query_api("listClusters", **args)
            if clusters:
                self.cluster = clusters["cluster"][0]
                self.result["cluster"] = self.cluster["name"]
            else:
                self.module.fail_json(msg="Cluster %s not found." % cluster_name)
        return self._get_by_key(key=key, my_dict=self.cluster)

    def get_storage(self, key=None):
        if not self.storage:
            storage_pool_name = self.module.params.get("storage")
            if not storage_pool_name:
                return None
            args = {
                "name": storage_pool_name,
            }
            storage_pools = self.query_api("listStoragePools", **args)
            if storage_pools:
                self.storage = storage_pools["storagepool"][0]
                self.result["storage"] = self.storage["name"]
            else:
                self.module.fail_json(msg="Storage pool %s not found." % storage_pool_name)
        return self._get_by_key(key=key, my_dict=self.storage)

    def get_configuration(self):
        configuration = None
        args = self._get_common_configuration_args()
        args["fetch_list"] = True
        configurations = self.query_api("listConfigurations", **args)
        if not configurations:
            self.module.fail_json(msg="Configuration %s not found." % args["name"])
        for config in configurations:
            if args["name"] == config["name"]:
                configuration = config
        return configuration

    def get_value(self):
        value = str(self.module.params.get("value"))
        if value in ("True", "False"):
            value = value.lower()
        return value

    def present_configuration(self):
        configuration = self.get_configuration()
        args = self._get_common_configuration_args()
        args["value"] = self.get_value()
        empty_value = args["value"] in [None, ""] and configuration is not None and "value" not in configuration
        if self.has_changed(args, configuration, ["value"]) and not empty_value:
            self.result["changed"] = True
            if not self.module.check_mode:
                res = self.query_api("updateConfiguration", **args)
                configuration = res["configuration"]
        return configuration

    def get_result(self, resource):
        self.result = super(AnsibleCloudStackConfiguration, self).get_result(resource)
        if self.account:
            self.result["account"] = self.account["name"]
            # TODO: buggy?
            self.result["domain"] = self.domain["path"] if self.domain else None
        elif self.zone:
            self.result["zone"] = self.zone["name"]
        return self.result


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            value=dict(type="str", required=True),
            zone=dict(type="str"),
            storage=dict(type="str"),
            cluster=dict(type="str"),
            account=dict(type="str"),
            domain=dict(type="str", default="ROOT"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        supports_check_mode=True,
    )

    aconfiguration = AnsibleCloudStackConfiguration(module)
    configuration = aconfiguration.present_configuration()
    result = aconfiguration.get_result(configuration)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
