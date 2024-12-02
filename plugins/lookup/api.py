# Copyright (c) 2024, Lorenzo Tanganelli
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
name: api
author: Lorenzo Tanganelli (@tanganellilore)
short_description: Iteract with the Cloudstack API via lookup
requirements:
  - None
description:
  - Returns GET requests from the Cloudstack API.
options:
  _terms:
    description:
      - The endpoint to query, i.e. listUserData, listVirtualMachines, etc.
    required: True
  query_params:
    description:
      - The query parameters to search for in the form of key/value pairs.
    type: dict
    required: False
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
notes:
  - If the query is not filtered properly this can cause a performance impact.
"""

EXAMPLES = """
- name: List all UserData from the API
  set_fact:
    controller_settings: "{{ lookup('ngine_io.cloudstack.api', 'listUserData', query_params={ 'listall': true }) }}"

- name: List all Virtual Machines from the API
  set_fact:
    virtual_machines: "{{ lookup('ngine_io.cloudstack.api', 'listVirtualMachines') }}"

- name: List specific Virtual Machines from the API
  set_fact:
    virtual_machines: "{{ lookup('ngine_io.cloudstack.api', 'listVirtualMachines', query_params={ 'name': 'myvmname' }) }}"
"""

RETURN = """
_raw:
  description:
    - Response from the API
  type: dict
  returned: on successful request
"""

from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError
from ansible.module_utils._text import to_native
from ansible.utils.display import Display

from ..module_utils.cloudstack_api import AnsibleCloudStackAPI


class LookupModule(LookupBase):
    display = Display()

    def handle_error(self, **kwargs):
        raise AnsibleError(to_native(kwargs.get("msg")))

    def warn_callback(self, warning):
        self.display.warning(warning)

    def run(self, terms, variables=None, **kwargs):
        if len(terms) != 1:
            raise AnsibleError("You must pass exactly one endpoint to query")

        self.set_options(direct=kwargs)

        module = AnsibleCloudStackAPI(argument_spec={}, direct_params=kwargs, error_callback=self.handle_error, warn_callback=self.warn_callback)

        args = {}
        if self.get_option("query_params"):
            args.update(self.get_option("query_params", {}))

        res = module.query_api(terms[0], **args)

        if res is None:
            return []
        if isinstance(res, list):
            return res

        return [res]
