#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020, Rafael del valle <rafael@privaz.io>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import os
import traceback
import yaml

DOCUMENTATION = r'''
    name: cloudstack
    plugin_type: inventory
    short_description: Apache CloudStack inventory source
    author: Rafael del Valle (@rvalle)
    version_added: 1.2.0
    description:
        - Get inventory hosts from Apache CloudStack
        - Allows filtering and grouping inventory hosts.
        - |
            Uses an YAML configuration file ending with either I(cloudstack.yml) or I(cloudstack.yaml) 
            to set parameter values (also see examples).
    options:
        plugin:
            description: Token that ensures this is a source file for the 'cloudstack' plugin.
            type: string
            required: True
            choices: [ cloudstack ]
        hostname:
            description: |
                Field to match the hostname. Note v4_main_ip corresponds to the primary ipv4address of the first nic 
                adapter of the instance.
            type: string
            default: v4_main_ip
            choices:
                - v4_main_ip
                - hostname
        filter_by_zone:
            description: Only return servers filtered in the provided zone
            type: string
    extends_documentation_fragment:
        - constructed
        - ngine_io.cloudstack.cloudstack                 
'''

EXAMPLES = '''
'''

# The J2 Template takes 'instance' object as returned from ACS and returns 'instance' object as returned by
# This inventory plugin.
INVENTORY_NORMALIZATION_J2 = '''
---
instance:
  name: {{instance.instancename}}
  v4_main_ip: {{instance.nic[0].ipaddress}}
  hostname: {{instance.hostname | lower }}
'''


from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, AnsibleError
from ansible.module_utils.basic import missing_required_lib
from ..module_utils.cloudstack import HAS_LIB_CS, cs_get_api_config
from jinja2 import Template


try:
    from cs import CloudStack, CloudStackException
except ImportError:
    pass


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'ngine_io.cloudstack.cloudstack'

    def __init__(self):
        super().__init__()
        if not HAS_LIB_CS:
            raise AnsibleError(missing_required_lib('cs'))
        self._cs=None
        self._normalization_template = Template(INVENTORY_NORMALIZATION_J2)

    def init_cs(self, config):
        api_config = self.get_api_config(config)
        self._cs = CloudStack(**api_config)

    @property
    def cs(self):
        return self._cs

    def get_api_config(self, inventory_config):
        # TODO: this should work with self._options
        api_config = cs_get_api_config(inventory_config)
        return api_config

    def query_api(self, command, **args):
        res = getattr(self.cs, command)(**args)

        if 'errortext' in res:
            raise AnsibleError(res['errortext'])

        return res

    def verify_file(self, path):
        """return true/false if this is possibly a valid file for this plugin to consume"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('cloudstack.yaml', 'cloudstack.yml')):
                valid = True
        return valid

    def get_filters(self):
        # Filtering as supported by ACS goes here
        args = {
            'fetch_list': True
        }

        return args

    def normalize_instance_data(self, instance):
        inventory_instance_str = self._normalization_template.render(instance=instance)
        inventory_instance = yaml.load(inventory_instance_str)
        return inventory_instance['instance']

    def parse(self, inventory, loader, path, cache=False):

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        # This is the inventory Config
        config = self._read_config_data(path)

        # We Initialize the query_api
        self.init_cs(config)

        # All Hosts from
        self.inventory.add_group('cloudstack')

        # The ansible_host preference
        hostname_preference = self.get_option('hostname')

        # Retrieve the filtered list of instances
        instances = self.query_api('listVirtualMachines', **self.get_filters())

        for instance in instances:

            # we normalize the instance data using the embedded J2 template
            instance = self.normalize_instance_data(instance)

            inventory_name = instance['name']
            self.inventory.add_host(inventory_name, group='cloudstack')

            for attribute, value in instance.items():
                # Add all available attributes
                self.inventory.set_variable(inventory_name, attribute, value)

            # set hostname preference
            self.inventory.set_variable(inventory_name, 'ansible_host', instance[hostname_preference])

            # Use constructed if applicable
            strict = self.get_option('strict')

            # Composed variables
            self._set_composite_vars(self.get_option('compose'), instance, inventory_name, strict=strict)

            # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
            self._add_host_to_composed_groups(self.get_option('groups'), instance, inventory_name, strict=strict)

            # Create groups based on variable values and add the corresponding hosts to it
            self._add_host_to_keyed_groups(self.get_option('keyed_groups'), instance, inventory_name, strict=strict)
