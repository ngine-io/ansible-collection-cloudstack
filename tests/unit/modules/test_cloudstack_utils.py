from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import unittest
from plugins.module_utils import cloudstack


class CloudstackUtilsTestCase(unittest.TestCase):

    def test_accessing_argument_spec(self):
        config_spec = cloudstack.cs_argument_spec()
        timeout = config_spec['api_timeout']['default']
        pass