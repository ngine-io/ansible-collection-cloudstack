#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: custom_action
short_description: Manages custom actions of extensions on Apache CloudStack based clouds.
description:
    - Create, update and remove custom actions of an extension.
    - Running a custom action is not in the scope of this module, as it is not idempotent.
author: René Moser (@resmo)
version_added: 3.4.0
options:
  name:
    description:
      - Name of the custom action.
    type: str
    required: true
  extension:
    description:
      - Name of the extension the custom action belongs to.
      - The extension must exist on I(state=present).
      - A custom action can not be moved to another extension.
    type: str
    required: true
  description:
    description:
      - Description of the custom action.
    type: str
  resource_type:
    description:
      - Resource type the custom action is available for.
    type: str
    choices: [ VirtualMachine ]
  allowed_role_types:
    description:
      - Role types allowed to run the custom action.
      - Defaults to C(Admin) when the custom action is created.
    type: list
    elements: str
    choices: [ Admin, DomainAdmin, ResourceAdmin, User, Unknown ]
  parameters:
    description:
      - Parameters of the custom action.
      - The given parameters replace the existing parameters as a whole, they are not merged.
      - Not considered when not set.
    type: list
    elements: dict
    suboptions:
      name:
        description:
          - Name of the parameter.
        type: str
        required: true
      type:
        description:
          - Type of the parameter.
        type: str
        choices: [ STRING, BOOLEAN, NUMBER, DATE ]
        default: STRING
      required:
        description:
          - Whether the parameter is mandatory when the custom action is run.
        type: bool
        default: false
      validation_format:
        description:
          - Format the value of the parameter is validated against.
          - Not every format is accepted for every I(parameters.type), C(DECIMAL) is only valid for
            I(parameters.type=NUMBER), the remaining formats only for I(parameters.type=STRING).
        type: str
        choices: [ NONE, URL, EMAIL, PASSWORD, UUID, DECIMAL ]
        default: NONE
      value_options:
        description:
          - List of values the parameter is limited to.
        type: list
        elements: str
  cleanup_parameters:
    description:
      - Whether to remove all parameters of an existing custom action.
      - Mutually exclusive with I(parameters).
    type: bool
  details:
    description:
      - Details of the custom action as key/value pairs.
      - The given details replace the existing details as a whole, they are not merged.
      - Not considered when not set.
    type: dict
  cleanup_details:
    description:
      - Whether to remove all details of an existing custom action.
      - Mutually exclusive with I(details).
    type: bool
  enabled:
    description:
      - Whether the custom action is enabled or not.
      - Custom actions are created disabled.
    type: bool
  success_message:
    description:
      - Message used on successful execution of the custom action.
      - The placeholders C({{actionName}}), C({{extensionName}}) and C({{resourceName}}) are substituted by CloudStack.
    type: str
  error_message:
    description:
      - Message used on failure during execution of the custom action.
      - The placeholders C({{actionName}}), C({{extensionName}}) and C({{resourceName}}) are substituted by CloudStack.
    type: str
  timeout:
    description:
      - Timeout in seconds to wait for the custom action to complete before failing.
    type: int
  state:
    description:
      - State of the custom action.
    type: str
    choices: [ present, absent ]
    default: present
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure a custom action is present
  ngine_io.cloudstack.custom_action:
    name: reset-appliance
    extension: my-orchestrator
    description: Reset the appliance
    resource_type: VirtualMachine
    enabled: true
    parameters:
      - name: force
        type: BOOLEAN
      - name: reason
        required: true

- name: Ensure a custom action is restricted to admins
  ngine_io.cloudstack.custom_action:
    name: reset-appliance
    extension: my-orchestrator
    allowed_role_types:
      - Admin
      - DomainAdmin

- name: Ensure a custom action has no parameters
  ngine_io.cloudstack.custom_action:
    name: reset-appliance
    extension: my-orchestrator
    cleanup_parameters: true

- name: Ensure a custom action is disabled
  ngine_io.cloudstack.custom_action:
    name: reset-appliance
    extension: my-orchestrator
    enabled: false

- name: Ensure a custom action is absent
  ngine_io.cloudstack.custom_action:
    name: reset-appliance
    extension: my-orchestrator
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the custom action.
  returned: success
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
name:
  description: Name of the custom action.
  returned: success
  type: str
  sample: reset-appliance
description:
  description: Description of the custom action.
  returned: success
  type: str
  sample: Reset the appliance
extension:
  description: Name of the extension the custom action belongs to.
  returned: success
  type: str
  sample: my-orchestrator
extension_id:
  description: UUID of the extension the custom action belongs to.
  returned: success
  type: str
  sample: 0d5a5b1c-1f7e-4e0e-9b1f-6f9a5f0f2f01
resource_type:
  description: Resource type the custom action is available for.
  returned: success
  type: str
  sample: VirtualMachine
allowed_role_types:
  description: Role types allowed to run the custom action.
  returned: success
  type: list
  sample: [ "Admin" ]
parameters:
  description: Parameters of the custom action.
  returned: success
  type: list
  sample: [ { "name": "force", "type": "BOOLEAN", "validationformat": "NONE", "required": false } ]
details:
  description: Details of the custom action.
  returned: success
  type: dict
  sample: { "vendor": "acme" }
enabled:
  description: Whether the custom action is enabled or not.
  returned: success
  type: bool
  sample: true
success_message:
  description: Message used on successful execution of the custom action.
  returned: success
  type: str
  sample: Completed {{actionName}} for {{resourceName}}
error_message:
  description: Message used on failure during execution of the custom action.
  returned: success
  type: str
  sample: Failed {{actionName}} for {{resourceName}}
timeout:
  description: Timeout in seconds to wait for the custom action to complete.
  returned: success
  type: int
  sample: 3
created:
  description: Date the custom action was created.
  returned: success
  type: str
  sample: 2026-08-23T12:58:00+0000
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together

# CloudStack applies these when a parameter does not spell them out, so the
# wanted parameters must carry them to compare against what the API returns.
PARAMETER_DEFAULT_TYPE = "STRING"
PARAMETER_DEFAULT_VALIDATION_FORMAT = "NONE"


class AnsibleCloudStackCustomAction(AnsibleCloudStack):
    """AnsibleCloudStackCustomAction"""

    def __init__(self, module):
        super(AnsibleCloudStackCustomAction, self).__init__(module)
        self.returns = {
            "extensionid": "extension_id",
            "extensionname": "extension",
            "resourcetype": "resource_type",
            "allowedroletypes": "allowed_role_types",
            "successmessage": "success_message",
            "errormessage": "error_message",
            "timeout": "timeout",
            "enabled": "enabled",
            "details": "details",
            "parameters": "parameters",
        }

    def get_extension_id(self):
        name = self.module.params.get("extension")
        extensions = self.query_api("listExtensions", name=name)
        if not extensions:
            self.fail_json(msg="Extension %s not found" % name)
        return extensions["extension"][0]["id"]

    def get_custom_action(self):
        args = {
            "extensionid": self.get_extension_id(),
            "name": self.module.params.get("name"),
        }
        custom_actions = self.query_api("listCustomActions", **args)
        if custom_actions:
            # The name filter of listCustomActions matches exactly.
            return custom_actions["extensioncustomaction"][0]
        return None

    def _get_wanted_details(self):
        details = self.module.params.get("details")
        if details is None:
            return None
        return dict((str(key), str(value)) for key, value in details.items())

    def _has_details_changed(self, custom_action):
        wanted = self._get_wanted_details()
        if wanted is None:
            return False

        current = dict((str(key), str(value)) for key, value in (custom_action.get("details") or {}).items())
        if wanted == current:
            return False

        self.result["diff"]["before"]["details"] = current
        self.result["diff"]["after"]["details"] = wanted
        return True

    def _get_wanted_parameters(self):
        """Normalize the parameters so they can be compared with what the API returns."""
        parameters = self.module.params.get("parameters")
        if parameters is None:
            return None

        wanted = []
        for parameter in parameters:
            entry = {
                "name": parameter["name"],
                "type": (parameter.get("type") or PARAMETER_DEFAULT_TYPE).upper(),
                "required": bool(parameter.get("required")),
                "validationformat": (parameter.get("validation_format") or PARAMETER_DEFAULT_VALIDATION_FORMAT).upper(),
            }
            value_options = parameter.get("value_options")
            if value_options:
                entry["valueoptions"] = [str(value) for value in value_options]
            wanted.append(entry)
        return wanted

    @staticmethod
    def _get_current_parameters(custom_action):
        current = []
        for parameter in custom_action.get("parameters") or []:
            entry = {
                "name": parameter.get("name"),
                "type": (parameter.get("type") or PARAMETER_DEFAULT_TYPE).upper(),
                "required": bool(parameter.get("required")),
                "validationformat": (parameter.get("validationformat") or PARAMETER_DEFAULT_VALIDATION_FORMAT).upper(),
            }
            value_options = parameter.get("valueoptions")
            if value_options:
                entry["valueoptions"] = [str(value) for value in value_options]
            current.append(entry)
        return current

    def _have_parameters_changed(self, custom_action):
        wanted = self._get_wanted_parameters()
        if wanted is None:
            return False

        current = self._get_current_parameters(custom_action)
        if wanted == current:
            return False

        self.result["diff"]["before"]["parameters"] = current
        self.result["diff"]["after"]["parameters"] = wanted
        return True

    @staticmethod
    def _to_api_parameters(wanted):
        """The API takes valueoptions comma separated, it returns them as a list."""
        api_parameters = []
        for parameter in wanted:
            entry = dict(parameter)
            if "valueoptions" in entry:
                entry["valueoptions"] = ",".join(entry["valueoptions"])
            api_parameters.append(entry)
        return api_parameters

    def _has_enabled_changed(self, custom_action):
        """Compare booleans without has_changed().

        has_changed() casts the value it finds in the resource to int to compare
        it with a bool, which rewrites "enabled": true into "enabled": 1 in the
        resource that is returned to the user.
        """
        wanted = self.module.params.get("enabled")
        if wanted is None:
            return False

        current = custom_action.get("enabled")
        if bool(current) == bool(wanted):
            return False

        self.result["diff"]["before"]["enabled"] = bool(current)
        self.result["diff"]["after"]["enabled"] = bool(wanted)
        return True

    def _have_role_types_changed(self, custom_action):
        wanted = self.module.params.get("allowed_role_types")
        if wanted is None:
            return False

        current = custom_action.get("allowedroletypes") or []
        if sorted(str(role).lower() for role in wanted) == sorted(str(role).lower() for role in current):
            return False

        self.result["diff"]["before"]["allowed_role_types"] = sorted(current)
        self.result["diff"]["after"]["allowed_role_types"] = sorted(wanted)
        return True

    def present_custom_action(self):
        custom_action = self.get_custom_action()
        if custom_action:
            custom_action = self._update_custom_action(custom_action)
        else:
            custom_action = self._create_custom_action()
        return custom_action

    def _create_custom_action(self):
        self.result["changed"] = True
        wanted_parameters = self._get_wanted_parameters()
        args = {
            "extensionid": self.get_extension_id(),
            "name": self.module.params.get("name"),
            "description": self.module.params.get("description"),
            "resourcetype": self.module.params.get("resource_type"),
            "allowedroletypes": self.module.params.get("allowed_role_types"),
            "details": self._get_wanted_details(),
            "parameters": self._to_api_parameters(wanted_parameters) if wanted_parameters else None,
            "enabled": self.module.params.get("enabled"),
            "successmessage": self.module.params.get("success_message"),
            "errormessage": self.module.params.get("error_message"),
            "timeout": self.module.params.get("timeout"),
        }
        custom_action = None
        if not self.module.check_mode:
            res = self.query_api("addCustomAction", **args)
            custom_action = res["extensioncustomaction"]
            self.custom_action = custom_action
        return custom_action

    def _update_custom_action(self, custom_action):
        args = {
            "id": custom_action["id"],
            "description": self.module.params.get("description"),
            "resourcetype": self.module.params.get("resource_type"),
            "successmessage": self.module.params.get("success_message"),
            "errormessage": self.module.params.get("error_message"),
            "timeout": self.module.params.get("timeout"),
        }

        cleanup_details = self.module.params.get("cleanup_details")
        cleanup_parameters = self.module.params.get("cleanup_parameters")

        details_changed = self._has_details_changed(custom_action)
        parameters_changed = self._have_parameters_changed(custom_action)
        role_types_changed = self._have_role_types_changed(custom_action)
        enabled_changed = self._has_enabled_changed(custom_action)
        cleanup_details_needed = bool(cleanup_details) and bool(custom_action.get("details"))
        cleanup_parameters_needed = bool(cleanup_parameters) and bool(custom_action.get("parameters"))

        has_changed = self.has_changed(args, custom_action)
        if any(
            [
                has_changed,
                details_changed,
                parameters_changed,
                role_types_changed,
                enabled_changed,
                cleanup_details_needed,
                cleanup_parameters_needed,
            ]
        ):
            self.result["changed"] = True
            if details_changed:
                args["details"] = self._get_wanted_details()
            if parameters_changed:
                args["parameters"] = self._to_api_parameters(self._get_wanted_parameters())
            if role_types_changed:
                args["allowedroletypes"] = self.module.params.get("allowed_role_types")
            if enabled_changed:
                args["enabled"] = self.module.params.get("enabled")
            if cleanup_details:
                args["cleanupdetails"] = True
            if cleanup_parameters:
                args["cleanupparameters"] = True
            if not self.module.check_mode:
                res = self.query_api("updateCustomAction", **args)
                custom_action = res["extensioncustomaction"]
                self.custom_action = custom_action
        return custom_action

    def absent_custom_action(self):
        custom_action = self.get_custom_action()
        if custom_action:
            self.result["changed"] = True
            args = {
                "id": custom_action["id"],
            }
            if not self.module.check_mode:
                self.query_api("deleteCustomAction", **args)
        return custom_action


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            extension=dict(type="str", required=True),
            description=dict(type="str"),
            resource_type=dict(type="str", choices=["VirtualMachine"]),
            allowed_role_types=dict(
                type="list",
                elements="str",
                choices=["Admin", "DomainAdmin", "ResourceAdmin", "User", "Unknown"],
            ),
            parameters=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    type=dict(type="str", choices=["STRING", "BOOLEAN", "NUMBER", "DATE"], default="STRING"),
                    required=dict(type="bool", default=False),
                    validation_format=dict(
                        type="str",
                        choices=["NONE", "URL", "EMAIL", "PASSWORD", "UUID", "DECIMAL"],
                        default="NONE",
                    ),
                    value_options=dict(type="list", elements="str"),
                ),
            ),
            cleanup_parameters=dict(type="bool"),
            details=dict(type="dict"),
            cleanup_details=dict(type="bool"),
            enabled=dict(type="bool"),
            success_message=dict(type="str"),
            error_message=dict(type="str"),
            timeout=dict(type="int"),
            state=dict(type="str", choices=["present", "absent"], default="present"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        mutually_exclusive=[
            ("details", "cleanup_details"),
            ("parameters", "cleanup_parameters"),
        ],
        supports_check_mode=True,
    )

    acs_custom_action = AnsibleCloudStackCustomAction(module)

    state = module.params.get("state")
    if state == "absent":
        custom_action = acs_custom_action.absent_custom_action()
    else:
        custom_action = acs_custom_action.present_custom_action()

    result = acs_custom_action.get_result(custom_action)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
