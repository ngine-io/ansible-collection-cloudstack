#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = """
---
module: iso
short_description: Manages ISO images on Apache CloudStack based clouds.
description:
  - Register, attach, detach, and remove ISO images.
author: René Moser (@resmo)
version_added: 0.1.0
options:
  name:
    description:
      - Name of the ISO.
    type: str
    required: true
  display_text:
    description:
      - Display text of the ISO.
      - If not specified, I(name) will be used.
    type: str
  url:
    description:
      - URL where the ISO can be downloaded from. Required if I(state) is present.
    type: str
  os_type:
    description:
      - Name of the OS that best represents the OS of this ISO. If the iso is bootable this parameter needs to be passed. Required if I(state) is present.
    type: str
  is_ready:
    description:
      - This flag is used for searching existing ISOs. If set to C(true), it will only list ISO ready for deployment e.g.
        successfully downloaded and installed. Recommended to set it to C(false).
    type: bool
    default: false
  is_public:
    description:
      - Register the ISO to be publicly available to all users. Only used if I(state) is present.
    type: bool
  is_featured:
    description:
      - Register the ISO to be featured. Only used if I(state) is present.
    type: bool
  is_dynamically_scalable:
    description:
      - Register the ISO having XS/VMware tools installed inorder to support dynamic scaling of VM cpu/memory. Only used if I(state) is present.
    type: bool
  checksum:
    description:
      - The MD5 checksum value of this ISO. If set, we search by checksum instead of name.
    type: str
  bootable:
    description:
      - Register the ISO to be bootable. Only used if I(state) is present.
    type: bool
  domain:
    description:
      - Domain the ISO is related to.
    type: str
  account:
    description:
      - Account the ISO is related to.
    type: str
  project:
    description:
      - Name of the project the ISO to be registered in.
    type: str
  zone:
    description:
      - Name of the zone you wish the ISO to be registered or deleted from.
      - Required when I(cross_zones) is C(false)
    type: str
  cross_zones:
    description:
      - Whether the ISO should be synced or removed across zones.
      - Mutually exclusive with I(zone).
    type: bool
    default: false
  iso_filter:
    description:
      - Name of the filter used to search for the ISO.
    type: str
    default: self
    choices: [ featured, self, selfexecutable,sharedexecutable,executable, community ]
  state:
    description:
      - State of the ISO.
      - C(attached) and C(detached) was added in version 3.1.0.
    type: str
    default: present
    choices: [ present, absent, attached, detached ]
  vm:
    description:
      - Virtual machine to attach or detach the ISO from.
      - Required when I(state) is C(attached) or C(detached).
    type: str
    version_added: 3.1.0
  poll_async:
    description:
      - Poll async jobs until job has finished.
    type: bool
    default: true
  tags:
    description:
      - List of tags. Tags are a list of dictionaries having keys I(key) and I(value).
      - "To delete all tags, set a empty list e.g. I(tags: [])."
    type: list
    elements: dict
    aliases: [ tag ]
extends_documentation_fragment:
- ngine_io.cloudstack.cloudstack
"""

EXAMPLES = """
- name: Register an ISO if ISO name does not already exist
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    url: http://mirror.switch.ch/ftp/mirror/debian-cd/current/amd64/iso-cd/debian-7.7.0-amd64-netinst.iso
    os_type: Debian GNU/Linux 7(64-bit)

- name: Register an ISO with given name if ISO md5 checksum does not already exist
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    url: http://mirror.switch.ch/ftp/mirror/debian-cd/current/amd64/iso-cd/debian-7.7.0-amd64-netinst.iso
    os_type: Debian GNU/Linux 7(64-bit)
    checksum: 0b31bccccb048d20b551f70830bb7ad0

- name: Remove an ISO by name
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    state: absent

- name: Remove an ISO by checksum
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    checksum: 0b31bccccb048d20b551f70830bb7ad0
    state: absent

- name: Register and attach an ISO to a VM
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    url: http://mirror.switch.ch/ftp/mirror/debian-cd/current/amd64/iso-cd/debian-7.7.0-amd64-netinst.iso
    os_type: Debian GNU/Linux 7(64-bit)
    vm: my-vm-01
    state: attached

- name: Attach an existing ISO to a VM
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    vm: my-vm-01
    state: attached

- name: Detach an ISO from a VM
  ngine_io.cloudstack.iso:
    name: Debian 7 64-bit
    zone: zone01
    vm: my-vm-01
    state: detached
"""

RETURN = """
---
id:
  description: UUID of the ISO.
  returned: success
  type: str
  sample: a6f7a5fc-43f8-11e5-a151-feff819cdc9f
name:
  description: Name of the ISO.
  returned: success
  type: str
  sample: Debian 7 64-bit
display_text:
  description: Text to be displayed of the ISO.
  returned: success
  type: str
  sample: Debian 7.7 64-bit minimal 2015-03-19
zone:
  description: Name of zone the ISO is registered in.
  returned: success
  type: str
  sample: zuerich
status:
  description: Status of the ISO.
  returned: success
  type: str
  sample: Successfully Installed
is_ready:
  description: True if the ISO is ready to be deployed from.
  returned: success
  type: bool
  sample: true
is_public:
  description: True if the ISO is public.
  returned: success
  type: bool
  sample: true
bootable:
  description: True if the ISO is bootable.
  returned: success
  type: bool
  sample: true
is_featured:
  description: True if the ISO is featured.
  returned: success
  type: bool
  sample: true
format:
  description: Format of the ISO.
  returned: success
  type: str
  sample: ISO
os_type:
  description: Type of the OS.
  returned: success
  type: str
  sample: CentOS 6.5 (64-bit)
checksum:
  description: MD5 checksum of the ISO.
  returned: success
  type: str
  sample: 0b31bccccb048d20b551f70830bb7ad0
created:
  description: Date of registering.
  returned: success
  type: str
  sample: 2015-03-29T14:57:06+0200
cross_zones:
  description: true if the ISO is managed across all zones, false otherwise.
  returned: success
  type: bool
  sample: false
vm:
  description: Name of the virtual machine the ISO is attached to.
  returned: success
  type: str
  sample: my-vm-01
domain:
  description: Domain the ISO is related to.
  returned: success
  type: str
  sample: example domain
account:
  description: Account the ISO is related to.
  returned: success
  type: str
  sample: example account
project:
  description: Project the ISO is related to.
  returned: success
  type: str
  sample: example project
tags:
  description: List of resource tags associated with the ISO.
  returned: success
  type: dict
  sample: '[ { "key": "foo", "value": "bar" } ]'
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.cloudstack import AnsibleCloudStack, cs_argument_spec, cs_required_together


class AnsibleCloudStackIso(AnsibleCloudStack):
    """AnsibleCloudStackIso"""

    def __init__(self, module):
        super(AnsibleCloudStackIso, self).__init__(module)
        self.returns = {
            "checksum": "checksum",
            "status": "status",
            "isready": "is_ready",
            "crossZones": "cross_zones",
            "format": "format",
            "ostypename": "os_type",
            "isfeatured": "is_featured",
            "bootable": "bootable",
            "ispublic": "is_public",
        }
        self.iso = None

    def _get_common_args(self):
        return {
            "name": self.module.params.get("name"),
            "displaytext": self.get_or_fallback("display_text", "name"),
            "isdynamicallyscalable": self.module.params.get("is_dynamically_scalable"),
            "ostypeid": self.get_os_type("id"),
            "bootable": self.module.params.get("bootable"),
        }

    def register_iso(self):
        args = self._get_common_args()
        args.update(
            {
                "domainid": self.get_domain("id"),
                "account": self.get_account("name"),
                "projectid": self.get_project("id"),
                "checksum": self.module.params.get("checksum"),
                "isfeatured": self.module.params.get("is_featured"),
                "ispublic": self.module.params.get("is_public"),
            }
        )

        if not self.module.params.get("cross_zones"):
            args["zoneid"] = self.get_zone(key="id")
        else:
            args["zoneid"] = -1

        if args["bootable"] and not args["ostypeid"]:
            self.module.fail_json(msg="OS type 'os_type' is required if 'bootable=true'.")

        args["url"] = self.module.params.get("url")
        if not args["url"]:
            self.module.fail_json(msg="URL is required.")

        self.result["changed"] = True
        if not self.module.check_mode:
            res = self.query_api("registerIso", **args)
            self.iso = res["iso"][0]
        return self.iso

    def present_iso(self):
        state = self.module.params.get("state")
        iso = self.get_iso()

        if state == "detached":
            iso = self.detach_iso(iso)
        else:
            if not iso:
                iso = self.register_iso()
            else:
                iso = self.update_iso(iso)

            if state == "attached":
                iso = self.attach_iso(iso)

        if iso:
            iso = self.ensure_tags(resource=iso, resource_type="ISO")
            self.iso = iso
        return iso

    def attach_iso(self, iso):
        if not iso:
            return iso

        vm = self.get_vm(filter_zone=False)
        if vm.get("isoid") == iso["id"]:
            return iso

        self.result["changed"] = True
        if not self.module.check_mode:
            args = {
                "id": iso["id"],
                "virtualmachineid": vm["id"],
            }
            res = self.query_api("attachIso", **args)
            poll_async = self.module.params.get("poll_async")
            if poll_async:
                self.poll_job(res, "iso")

            # Refresh cached values after VM ISO attachment state has changed.
            self.vm = None
            self.iso = None
            iso = self.get_iso()
        return iso

    def detach_iso(self, iso):
        if not iso:
            return iso

        vm = self.get_vm(filter_zone=False)
        if vm.get("isoid") != iso["id"]:
            return iso

        self.result["changed"] = True
        if not self.module.check_mode:
            args = {
                "virtualmachineid": vm["id"],
            }
            res = self.query_api("detachIso", **args)
            poll_async = self.module.params.get("poll_async")
            if poll_async:
                self.poll_job(res, "iso")

            # Refresh cached values after VM ISO detachment state has changed.
            self.vm = None
            self.iso = None
            iso = self.get_iso()
        return iso

    def update_iso(self, iso):
        args = self._get_common_args()
        args.update(
            {
                "id": iso["id"],
            }
        )
        if self.has_changed(args, iso):
            self.result["changed"] = True

            if not self.module.params.get("cross_zones"):
                args["zoneid"] = self.get_zone(key="id")
            else:
                # Workaround API does not return cross_zones=true
                self.result["cross_zones"] = True
                args["zoneid"] = -1

            if not self.module.check_mode:
                res = self.query_api("updateIso", **args)
                self.iso = res["iso"]
        return self.iso

    def get_iso(self):
        if not self.iso:
            args = {
                "isready": self.module.params.get("is_ready"),
                "isofilter": self.module.params.get("iso_filter"),
                "domainid": self.get_domain("id"),
                "account": self.get_account("name"),
                "projectid": self.get_project("id"),
            }

            if not self.module.params.get("cross_zones"):
                args["zoneid"] = self.get_zone(key="id")

            # if checksum is set, we only look on that.
            checksum = self.module.params.get("checksum")
            if not checksum:
                args["name"] = self.module.params.get("name")

            isos = self.query_api("listIsos", **args)
            if isos:
                if not checksum:
                    self.iso = isos["iso"][0]
                else:
                    for i in isos["iso"]:
                        if i["checksum"] == checksum:
                            self.iso = i
                            break
        return self.iso

    def absent_iso(self):
        iso = self.get_iso()
        if iso:
            self.result["changed"] = True

            args = {
                "id": iso["id"],
                "projectid": self.get_project("id"),
            }

            if not self.module.params.get("cross_zones"):
                args["zoneid"] = self.get_zone(key="id")

            if not self.module.check_mode:
                res = self.query_api("deleteIso", **args)
                poll_async = self.module.params.get("poll_async")
                if poll_async:
                    self.poll_job(res, "iso")
        return iso

    def get_result(self, resource):
        super(AnsibleCloudStackIso, self).get_result(resource)
        if self.module.params.get("state") in ["attached", "detached"]:
            self.result["vm"] = self.get_vm(key="name", filter_zone=False)

        # Workaround API does not return cross_zones=true
        if self.module.params.get("cross_zones"):
            self.result["cross_zones"] = True
            if "zone" in self.result:
                del self.result["zone"]
        return self.result


def main():
    argument_spec = cs_argument_spec()
    argument_spec.update(
        dict(
            name=dict(required=True),
            display_text=dict(),
            url=dict(),
            os_type=dict(),
            zone=dict(),
            cross_zones=dict(type="bool", default=False),
            iso_filter=dict(default="self", choices=["featured", "self", "selfexecutable", "sharedexecutable", "executable", "community"]),
            domain=dict(),
            account=dict(),
            project=dict(),
            vm=dict(type="str"),
            checksum=dict(),
            is_ready=dict(type="bool", default=False),
            bootable=dict(type="bool"),
            is_featured=dict(type="bool"),
            is_public=dict(type="bool"),
            is_dynamically_scalable=dict(type="bool"),
            state=dict(choices=["present", "absent", "attached", "detached"], default="present"),
            poll_async=dict(type="bool", default=True),
            tags=dict(type="list", elements="dict", aliases=["tag"]),
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_together=cs_required_together(),
        mutually_exclusive=(["zone", "cross_zones"],),
        required_if=[("state", "attached", ["vm"]), ("state", "detached", ["vm"])],
        supports_check_mode=True,
    )

    aiso = AnsibleCloudStackIso(module)

    state = module.params.get("state")
    if state in ["absent"]:
        iso = aiso.absent_iso()
    else:
        iso = aiso.present_iso()

    result = aiso.get_result(iso)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
