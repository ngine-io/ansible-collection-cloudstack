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
    extends_documentation_fragment:
        - ngine_io.cloudstack.cloudstack                 
'''

EXAMPLES = '''
'''


from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, AnsibleError
from ansible.module_utils.basic import missing_required_lib
from ..module_utils.cloudstack import HAS_LIB_CS, cs_get_api_config

try:
    from cs import CloudStack, CloudStackException
except ImportError:
    pass


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'ngine_io.cloudstack.cloudstack'

    def __init__(self):
        if not HAS_LIB_CS:
            raise AnsibleError(missing_required_lib('cs'))
        self._cs=None

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
        #hostname_preference = self.get_option('hostname')

        # Retrieve the filtered list of instances
        instances = self.query_api('listVirtualMachines', **self.get_filters())

        # Normalize its data
        # server = Vultr.normalize_result(server, SCHEMA)

        if instances:
            for v in instances:
                host = v['instancename']
                self.inventory.add_host(host, group='cloudstack')

                for attribute, value in v.items():
                    # Add all available attributes
                    self.inventory.set_variable(host, attribute, value)
'''
                # ip4v here is something like nic[0].ip
                #if hostname_preference != 'name':
                #    self.inventory.set_variable(server['name'], 'ansible_host', server[hostname_preference])

                # Use constructed if applicable
                strict = self.get_option('strict')

                # Composed variables
                self._set_composite_vars(self.get_option('compose'), server, server['name'], strict=strict)

                # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
                self._add_host_to_composed_groups(self.get_option('groups'), server, server['name'], strict=strict)

                # Create groups based on variable values and add the corresponding hosts to it
                self._add_host_to_keyed_groups(self.get_option('keyed_groups'), server, server['name'], strict=strict)
                
'''