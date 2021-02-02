==========================================
Apache CloudStack Collection Release Notes
==========================================

.. contents:: Topics


v2.0.0
======

Breaking Changes / Porting Guide
--------------------------------

- Authentication option using INI files e.g. ``cloudstack.ini`` has been removed. The only supported option to authenticate is by using the module params with fallback to the ENV variables.
- default zone deprecation - The `zone` param default value, across multiple modules, has been deprecated due to unreliable API (https://github.com/ngine-io/ansible-collection-cloudstack/pull/62).

v1.2.0
======

Minor Changes
-------------

- cs_instance - Fixed an edge case caused by `displaytext` not available (https://github.com/ngine-io/ansible-collection-cloudstack/pull/49).
- cs_network - Fixed constraints when creating networks. The param `gateway` is no longer required if the param `netmask` is given (https://github.com/ngine-io/ansible-collection-cloudstack/pull/54).

v1.1.0
======

Minor Changes
-------------

- Deprecated the funtionality of first returned zone to be the default zone because of an unreliable API. Zone will be required beginning with next major version 2.0.0.
- cs_ip_address - allow to pick a particular IP address for a network, available since CloudStack v4.13 (https://github.com/ngine-io/ansible-collection-cloudstack/issues/30).

v1.0.1
======

Minor Changes
-------------

- cs_configuration - Workaround for empty global settings idempotency (https://github.com/ngine-io/ansible-collection-cloudstack/pull/25).

v1.0.0
======

Minor Changes
-------------

- cs_vlan_ip_range - Added support to set IP range for system VMs (https://github.com/ngine-io/ansible-collection-cloudstack/pull/18)
- cs_vlan_ip_range - Added support to specify pod name (https://github.com/ngine-io/ansible-collection-cloudstack/pull/20)

v0.3.0
======

Minor Changes
-------------

- Added support for SSL CA cert verification (https://github.com/ngine-io/ansible-collection-cloudstack/pull/3)
