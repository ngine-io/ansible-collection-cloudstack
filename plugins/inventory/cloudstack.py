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


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'ngine_io.cloudstack.cloudstack'

    def __init__(self):
        if not HAS_LIB_CS:
            raise AnsibleError(missing_required_lib('cs'))

    def get_api_config(self, path):

        # this method will parse 'common format' inventory sources and
        # update any options declared in DOCUMENTATION as needed
        inventory_config = self._read_config_data(path)

        api_config = cs_get_api_config(inventory_config)

        return api_config

    def verify_file(self, path):
        """return true/false if this is possibly a valid file for this plugin to consume"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(('cloudstack.yaml', 'cloudstack.yml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=False):

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        api_config = self.get_api_config(path)

        """# example consuming options from inventory source
        mysession = apilib.session(user=self.get_option('api_user'),
                                   password=self.get_option('api_pass'),
                                   server=self.get_option('api_server')
                                   )
    
        # make requests to get data to feed into inventory
        mydata = mysession.getitall()"""

        # parse data and create inventory objects:
        """for colo in mydata:
            for server in mydata[colo]['servers']:
                self.inventory.add_host(server['name'])
                self.inventory.set_variable(server['name'], 'ansible_host', server['external_ip'])"""

        self.inventory.add_group('cloudstack')
        self.inventory.add_host('hello_world')
        self.inventory.set_variable('hello_world', 'ansible_host', '127.0.0.1')
        self.inventory.add_child('cloudstack', 'hello_world')
