#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: api_request
short_description: Executes ad-hoc Apache CloudStack API requests.
description:
    - Executes ad-hoc CloudStack API requests.
    - This is a command-style module and is never idempotent.
    - Request parameters can be provided either as free-form C(key=value) pairs after the command name or as a C(params) dictionary.
author: René Moser (@resmo)
version_added: 3.1.0
options:
  free_form:
    description:
      - API command followed by optional C(key=value) request parameters.
      - There is no actual parameter named C(free_form).
      - "Example: C(listVPCs keyword=my-vpc listall=true)."
    type: str
  command:
    description:
      - API command to execute, for example C(listVirtualMachines) or C(listCapabilities).
      - Optional when using the free-form syntax, where the first token is used as the command name.
    type: str
  params:
    description:
      - Arbitrary API parameters passed to the command.
      - Explicit C(params) values override free-form C(key=value) pairs with the same key.
    type: dict
    aliases: [ query_params ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
notes:
  - This module is not idempotent, nor supports check mode. This means, idempotency must be manually handled in your playbooks.
  - It always reports C(changed=true) when a request is executed successfully.
  - Free-form tokens after the command must be written as C(key=value).
"""

EXAMPLES = """
- name: Execute an API request with free-form parameters
  ngine_io.cloudstack.api_request: listVPCs keyword=my-vpc listall=true
  register: api_result

- name: Execute an API request with structured parameters
  ngine_io.cloudstack.api_request:
    command: listCapabilities
  register: api_result

- name: Execute an API request with explicit parameters
  ngine_io.cloudstack.api_request:
    command: listVirtualMachines
    params:
      keyword: my-vm
      listall: true
  register: api_result
"""

RETURN = """
---
command:
  description: API command that was executed.
  returned: success
  type: str
  sample: listCapabilities
params:
  description: Effective API parameters sent with the request.
  returned: success
  type: dict
  sample:
    keyword: my-vm
    listall: true
response:
  description: Raw CloudStack API response.
  returned: success
  type: raw
"""

import re
import shlex

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackAPIRequest(AnsibleCloudStack):
    """AnsibleCloudStackAPIRequest"""

    _FLOAT_RE = re.compile(r"^[+-]?\d+\.\d+$")
    _INT_RE = re.compile(r"^[+-]?\d+$")

    def _coerce_value(self, value):
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        if lower in ["none", "null"]:
            return None
        if self._INT_RE.match(value):
            return int(value)
        if self._FLOAT_RE.match(value):
            return float(value)
        return value

    def _parse_raw_params(self):
        raw_params = self.module.params.get("_raw_params") or self.module.params.get("free_form")
        if not raw_params:
            return None, {}

        try:
            tokens = shlex.split(raw_params)
        except ValueError as exc:
            self.fail_json(msg="Failed to parse free-form request: %s" % exc)

        if not tokens:
            self.fail_json(msg="Free-form request must include an API command")

        command = tokens[0]
        args = {}
        for token in tokens[1:]:
            if "=" not in token:
                self.fail_json(msg="Free-form argument '%s' must use key=value syntax" % token)

            key, value = token.split("=", 1)
            if not key:
                self.fail_json(msg="Free-form argument '%s' is missing a key" % token)
            args[key] = self._coerce_value(value)
        return command, args

    def get_request(self):
        raw_command, raw_args = self._parse_raw_params()

        command = self.module.params.get("command")
        if raw_command and command and raw_command != command:
            self.fail_json(msg="Conflicting command values provided in free-form arguments and 'command'")

        command = command or raw_command
        if not command:
            self.fail_json(msg="missing required arguments: command")

        params = raw_args
        explicit_params = self.module.params.get("params") or {}
        params.update(explicit_params)
        return command, params

    def execute(self):
        command, params = self.get_request()

        self.result["changed"] = True
        self.result["command"] = command
        self.result["params"] = params
        self.result["response"] = self.query_api(command, **params)
        return self.result


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            command=dict(type="str"),
            free_form=dict(type="str"),
            params=dict(type="dict", aliases=["query_params"]),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        supports_check_mode=False,
    )

    acs_api_request = AnsibleCloudStackAPIRequest(module)
    result = acs_api_request.execute()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
