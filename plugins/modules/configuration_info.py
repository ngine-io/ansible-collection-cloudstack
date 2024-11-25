#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: configuration_info
short_description: Gathering information about configurations from Apache CloudStack based clouds.
description:
  - Gathering information from the API about configurations.
author: Francisco Arencibia (@arencibiafrancisco)
version_added: 3.0.0
options:
  name:
    description:
      - Name of the configuration.
      - If not specified, information about all configurations is gathered.
    type: str
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Gather information about a specific configuration
  ngine_io.cloudstack.configuration_info:
    name: consoleproxy.sslEnabled
  register: config

- name: Show the returned results of the registered variable
  debug:
    msg: "{{ config }}"

- name: Gather information about all configurations
  ngine_io.cloudstack.configuration_info:
  register: configs

- name: Show information on all configurations
  debug:
    msg: "{{ configs }}"
"""

RETURN = """
---
configurations:
  description: A list of matching configurations.
  type: list
  returned: success
  contains:
    name:
      description: Name of the configuration.
      returned: success
      type: str
      sample: consoleproxy.sslEnabled
    value:
      description: Value of the configuration.
      returned: success
      type: str
      sample: true
    description:
      description: Description of the configuration.
      returned: success
      type: str
      sample: "Enable SSL for console proxy"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ngine_io.cloudstack.plugins.module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec


class AnsibleCloudStackConfigurationInfo(AnsibleCloudStack):

    def __init__(self, module):
        super(AnsibleCloudStackConfigurationInfo, self).__init__(module)
        self.returns = {
            "name": "name",
            "value": "value",
            "description": "description",
        }

    def get_configuration(self):
        args = {}
        if self.module.params["name"]:
            args["name"] = self.module.params["name"]
            configurations = self.query_api("listConfigurations", **args)
            if configurations and "configuration" in configurations:
                configurations = configurations["configuration"]
            else:
                configurations = []
        else:
            configurations = self.query_api("listConfigurations")
            if configurations and "configuration" in configurations:
                configurations = configurations["configuration"]
            else:
                configurations = []

        return {"configurations": [self.update_result(config) for config in configurations]}


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    acs_configuration_info = AnsibleCloudStackConfigurationInfo(module=module)
    result = acs_configuration_info.get_configuration()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
