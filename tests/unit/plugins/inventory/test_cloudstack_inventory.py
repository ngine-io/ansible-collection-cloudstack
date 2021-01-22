from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import unittest
import os

from ansible.parsing.dataloader import DataLoader
from plugins.inventory.cloudstack import InventoryModule


class InventoryModuleMock(InventoryModule):
    # Try to keep the InventoryModule clean without Unit Testing entry-points

    def __init__(self):
        super().__init__()
        self.loader = DataLoader()
        self._redirected_names = ['cloudstack']
        self._load_name = self.NAME

    def get_api_config_from_path(self, path):
        # We want to test get_api_config but we have mocked
        # How the configuration is read
        config = self._read_config_data(path)
        return self.get_api_config(config)


class InventoryTestCase(unittest.TestCase):

    def tearDown(self):
        # We clean up the cloudstack process environment after each test
        # As different test use different configurations
        for param in ['CONFIG', 'ENDPOINT', 'KEY', 'SECRET']:
            env_param = "CLOUDSTACK_{setting}".format(setting=param)
            if env_param in os.environ:
                os.environ.pop(env_param)

    def test_invalid_existing_file(self):
        # dummy test to get the environment setup
        self.assertFalse(InventoryModuleMock().verify_file("fixtures/wrong-inventory.ini"))

    def test_valid_file(self):
        # dummy test to get the environment setup
        self.assertTrue(InventoryModuleMock().verify_file("fixtures/test-not-configured.cloudstack.yml"))

    def test_full_configured_inventory_plugin(self):
        # We check that it is possible to configure all required settings in the inventory
        # plugin file
        api_config = InventoryModuleMock().get_api_config_from_path('fixtures/test-configured.cloudstack.yml')
        self.assertTrue(all([api_config['endpoint'], api_config['key'], api_config['secret']]))

    def test_environment_configuration_inventory_plugin(self):
        # We check that when using a not configured inventory plugin file
        # With environment variables providing the configuration a valid
        # configuration is achieved
        os.environ['CLOUDSTACK_ENDPOINT'] = 'http://localhost'
        os.environ['CLOUDSTACK_KEY'] = 'mykey'
        os.environ['CLOUDSTACK_SECRET'] = 'mysecret'
        api_config = InventoryModuleMock().get_api_config_from_path('fixtures/test-not-configured.cloudstack.yml')
        self.assertTrue(all([api_config['endpoint'], api_config['key'], api_config['secret']]))


if __name__ == '__main__':
    unittest.main()
