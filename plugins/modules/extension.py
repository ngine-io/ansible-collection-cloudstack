#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2026, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: extension
short_description: Manages extensions on Apache CloudStack based clouds.
description:
    - Create, update and remove extensions.
    - Register and unregister an extension with a resource.
author: René Moser (@resmo)
version_added: 3.4.0
options:
  name:
    description:
      - Name of the extension.
    type: str
    required: true
  extension_type:
    description:
      - Type of the extension.
      - Only considered on creation, it can not be changed afterwards.
    type: str
    choices: [ Orchestrator ]
    default: Orchestrator
  description:
    description:
      - Description of the extension.
    type: str
  path:
    description:
      - Relative path of the entry point of the extension.
      - Only considered on creation, it can not be changed afterwards.
      - When not given, CloudStack derives the path from I(name).
    type: str
  details:
    description:
      - Details of the extension as key/value pairs.
      - On I(state=present) the given details replace the existing details as a whole, they are not merged.
      - On I(state=register) the details are stored on the registration, not on the extension.
      - Not considered when not set.
    type: dict
  cleanup_details:
    description:
      - Whether to remove all details of an existing extension.
      - Only considered on I(state=present) and mutually exclusive with I(details).
    type: bool
  orchestrator_requires_prepare_vm:
    description:
      - Whether prepare VM is needed.
      - Only honored when I(extension_type=Orchestrator).
    type: bool
  extension_state:
    description:
      - State of the extension itself, not to be confused with I(state).
      - When not given, the state of an existing extension is left as it is, new extensions default to C(enabled).
    type: str
    choices: [ enabled, disabled ]
  cleanup:
    description:
      - Whether to remove the files of the extension from all management servers.
      - Only considered on I(state=absent).
    type: bool
    default: false
  resource_id:
    description:
      - ID of the resource to register the extension with.
      - Required on I(state=register) and I(state=unregister).
      - Names are not resolved, this must be the ID of the resource.
    type: str
  resource_type:
    description:
      - Type of the resource to register the extension with.
      - Required on I(state=register) and I(state=unregister).
    type: str
    choices: [ Cluster ]
  state:
    description:
      - State of the extension.
      - C(register) and C(unregister) manage the registration of an existing extension with a resource,
        they do not create or remove the extension itself.
    type: str
    choices: [ present, absent, register, unregister ]
    default: present
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Ensure an extension is present
  ngine_io.cloudstack.extension:
    name: my-orchestrator
    description: My custom orchestrator
    details:
      endpoint: https://orchestrator.example.com

- name: Ensure an extension is disabled
  ngine_io.cloudstack.extension:
    name: my-orchestrator
    extension_state: disabled

- name: Ensure an extension is registered with a cluster
  ngine_io.cloudstack.extension:
    name: my-orchestrator
    resource_id: 0d5a5b1c-1f7e-4e0e-9b1f-6f9a5f0f2f01
    resource_type: Cluster
    state: register

- name: Ensure an extension is unregistered from a cluster
  ngine_io.cloudstack.extension:
    name: my-orchestrator
    resource_id: 0d5a5b1c-1f7e-4e0e-9b1f-6f9a5f0f2f01
    resource_type: Cluster
    state: unregister

- name: Ensure an extension is absent including its files
  ngine_io.cloudstack.extension:
    name: my-orchestrator
    cleanup: true
    state: absent
"""

RETURN = """
---
id:
  description: UUID of the extension.
  returned: success
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
name:
  description: Name of the extension.
  returned: success
  type: str
  sample: my-orchestrator
description:
  description: Description of the extension.
  returned: success
  type: str
  sample: My custom orchestrator
extension_type:
  description: Type of the extension.
  returned: success
  type: str
  sample: Orchestrator
state:
  description: State of the extension.
  returned: success
  type: str
  sample: Enabled
path:
  description: Path of the entry point of the extension.
  returned: success
  type: str
  sample: /usr/share/cloudstack-management/extensions/my-orchestrator/my-orchestrator.sh
path_ready:
  description: Whether the entry point is ready on all management servers.
  returned: success
  type: bool
  sample: true
is_user_defined:
  description: Whether the extension was added by an admin.
  returned: success
  type: bool
  sample: true
orchestrator_requires_prepare_vm:
  description: Whether prepare VM is needed.
  returned: success
  type: bool
  sample: false
details:
  description: Details of the extension.
  returned: success
  type: dict
  sample: { "endpoint": "https://orchestrator.example.com" }
resources:
  description: Resources the extension is registered with.
  returned: success
  type: list
  sample: [ { "id": "0d5a5b1c-1f7e-4e0e-9b1f-6f9a5f0f2f01", "name": "cluster-01", "type": "Cluster" } ]
created:
  description: Date of the extension was created.
  returned: success
  type: str
  sample: 2026-08-23T12:09:39+0000
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackExtension(AnsibleCloudStack):
    """AnsibleCloudStackExtension"""

    def __init__(self, module):
        super(AnsibleCloudStackExtension, self).__init__(module)
        self.returns = {
            "type": "extension_type",
            "path": "path",
            "pathready": "path_ready",
            "isuserdefined": "is_user_defined",
            "orchestratorrequirespreparevm": "orchestrator_requires_prepare_vm",
            "details": "details",
            "resources": "resources",
        }

    def get_extension(self):
        args = {
            "name": self.module.params.get("name"),
            # Without this, registered resources are not part of the response.
            "details": "all",
        }
        extensions = self.query_api("listExtensions", **args)
        if extensions:
            # The name filter of listExtensions matches exactly.
            return extensions["extension"][0]

        return None

    def _get_extension_state(self):
        """Map the lower cased module choice onto what the API expects."""
        extension_state = self.module.params.get("extension_state")
        if extension_state is None:
            return None
        return extension_state.capitalize()

    def _get_wanted_details(self):
        details = self.module.params.get("details")
        if details is None:
            return None
        return dict((str(key), str(value)) for key, value in details.items())

    def _has_details_changed(self, extension):
        """Compare details as a whole, updateExtension replaces them, it does not merge."""
        wanted = self._get_wanted_details()
        if wanted is None:
            return False

        current = dict((str(key), str(value)) for key, value in (extension.get("details") or {}).items())
        if wanted == current:
            return False

        self.result["diff"]["before"]["details"] = current
        self.result["diff"]["after"]["details"] = wanted
        return True

    def _has_prepare_vm_changed(self, extension):
        """Compare booleans without has_changed().

        has_changed() casts the value it finds in the resource to int to compare
        it with a bool, which rewrites true into 1 in the resource that is
        returned to the user.
        """
        wanted = self.module.params.get("orchestrator_requires_prepare_vm")
        if wanted is None:
            return False

        current = extension.get("orchestratorrequirespreparevm")
        if bool(current) == bool(wanted):
            return False

        self.result["diff"]["before"]["orchestrator_requires_prepare_vm"] = bool(current)
        self.result["diff"]["after"]["orchestrator_requires_prepare_vm"] = bool(wanted)
        return True

    def present_extension(self):
        extension = self.get_extension()
        if extension:
            extension = self._update_extension(extension)
        else:
            extension = self._create_extension()
        return extension

    def _create_extension(self):
        self.result["changed"] = True
        args = {
            "name": self.module.params.get("name"),
            "type": self.module.params.get("extension_type"),
            "description": self.module.params.get("description"),
            "path": self.module.params.get("path"),
            "details": self._get_wanted_details(),
            "orchestratorrequirespreparevm": self.module.params.get("orchestrator_requires_prepare_vm"),
            "state": self._get_extension_state(),
        }
        extension = None
        if not self.module.check_mode:
            res = self.query_api("createExtension", **args)
            extension = res["extension"]
        return extension

    def _warn_on_immutable_args(self, extension):
        for param, key, label in [
            ("extension_type", "type", "extension_type"),
            ("path", "path", "path"),
        ]:
            value = self.module.params.get(param)
            if value and str(value) != str(extension.get(key) or ""):
                self.module.warn("%s can not be changed on an existing extension, current value is %s" % (label, extension.get(key)))

    def _update_extension(self, extension):
        self._warn_on_immutable_args(extension)

        args = {
            "id": extension["id"],
            "description": self.module.params.get("description"),
            "state": self._get_extension_state(),
        }

        cleanup_details = self.module.params.get("cleanup_details")
        details_changed = self._has_details_changed(extension)
        prepare_vm_changed = self._has_prepare_vm_changed(extension)
        cleanup_needed = bool(cleanup_details) and bool(extension.get("details"))

        if self.has_changed(args, extension) or details_changed or prepare_vm_changed or cleanup_needed:
            self.result["changed"] = True
            if details_changed:
                args["details"] = self._get_wanted_details()
            if prepare_vm_changed:
                args["orchestratorrequirespreparevm"] = self.module.params.get("orchestrator_requires_prepare_vm")
            if cleanup_details:
                args["cleanupdetails"] = True
            if not self.module.check_mode:
                res = self.query_api("updateExtension", **args)
                extension = res["extension"]
                self.extension = extension
        return extension

    def absent_extension(self):
        extension = self.get_extension()
        if extension:
            self.result["changed"] = True
            args = {
                "id": extension["id"],
                "cleanup": self.module.params.get("cleanup"),
            }
            if not self.module.check_mode:
                self.query_api("deleteExtension", **args)
        return extension

    def _get_registered_resource(self, extension):
        resource_id = self.module.params.get("resource_id")
        resource_type = self.module.params.get("resource_type")
        for resource in extension.get("resources") or []:
            if resource.get("id") != resource_id:
                continue
            current_type = resource.get("type")
            if current_type and current_type.lower() != resource_type.lower():
                continue
            return resource
        return None

    def register_extension(self):
        extension = self.get_extension()
        if not extension:
            self.fail_json(msg="Extension %s not found, it must exist before it can be registered" % self.module.params.get("name"))

        if self._get_registered_resource(extension) is None:
            self.result["changed"] = True
            args = {
                "extensionid": extension["id"],
                "resourceid": self.module.params.get("resource_id"),
                "resourcetype": self.module.params.get("resource_type"),
                "details": self._get_wanted_details(),
            }
            if not self.module.check_mode:
                self.query_api("registerExtension", **args)
                self.extension = None
                extension = self.get_extension()
        return extension

    def unregister_extension(self):
        extension = self.get_extension()
        if not extension:
            self.fail_json(msg="Extension %s not found, it must exist before it can be unregistered" % self.module.params.get("name"))

        if self._get_registered_resource(extension) is not None:
            self.result["changed"] = True
            args = {
                "extensionid": extension["id"],
                "resourceid": self.module.params.get("resource_id"),
                "resourcetype": self.module.params.get("resource_type"),
            }
            if not self.module.check_mode:
                self.query_api("unregisterExtension", **args)
                self.extension = None
                extension = self.get_extension()
        return extension


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type="str", required=True),
            extension_type=dict(type="str", choices=["Orchestrator"], default="Orchestrator"),
            description=dict(type="str"),
            path=dict(type="str"),
            details=dict(type="dict"),
            cleanup_details=dict(type="bool"),
            orchestrator_requires_prepare_vm=dict(type="bool"),
            extension_state=dict(type="str", choices=["enabled", "disabled"]),
            cleanup=dict(type="bool", default=False),
            resource_id=dict(type="str"),
            resource_type=dict(type="str", choices=["Cluster"]),
            state=dict(type="str", choices=["present", "absent", "register", "unregister"], default="present"),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        required_if=[
            ("state", "register", ["resource_id", "resource_type"]),
            ("state", "unregister", ["resource_id", "resource_type"]),
        ],
        mutually_exclusive=[
            ("details", "cleanup_details"),
        ],
        supports_check_mode=True,
    )

    acs_extension = AnsibleCloudStackExtension(module)

    state = module.params.get("state")
    if state == "absent":
        extension = acs_extension.absent_extension()
    elif state == "register":
        extension = acs_extension.register_extension()
    elif state == "unregister":
        extension = acs_extension.unregister_extension()
    else:
        extension = acs_extension.present_extension()

    result = acs_extension.get_result(extension)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
