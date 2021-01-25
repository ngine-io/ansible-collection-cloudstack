import unittest

import os

import urllib.request, json, yaml

from cs import CloudStack, read_config, CloudStackException
from jinja2 import Template
from plugins.inventory.cloudstack import INVENTORY_NORMALIZATION_J2, InventoryModule

with urllib.request.urlopen("http://localhost:8888/admin.json") as url:
    # get the CloudStack simulator keys
    admin = json.loads(url.read().decode())
    print(admin)

# Configure the CloudStack endpoing
#os.environ['CLOUDSTACK_ENDPOINT'] = 'http://localhost:8888/client/api'
#os.environ['CLOUDSTACK_KEY'] = admin['apikey']
#os.environ['CLOUDSTACK_SECRET'] = admin['secretkey']

# Production endpoint
#os.environ['CLOUDSTACK_ENDPOINT'] = 'https://pvz2.core/client/api'
#os.environ['CLOUDSTACK_KEY'] = '-_uO5b1A8Ppc8z5Ik0hXWti-gSfG8SbhBGLb08dr3Gs9ST2K9QUOCzvmmjY5hjOq48YkaMskldyQkcLGJQVoYg'
#os.environ['CLOUDSTACK_SECRET'] = 'EyXqQeMboOjmmQgNvEs4Yq82xmPICxUfayiTRgVqcxYc4SLem-psdnU7vWGblPYxLPq5XJbIo6dKcf9SJ2YkHA'

# Test environment
os.environ['CLOUDSTACK_ENDPOINT'] = 'https://pvz3.core/client/api'
os.environ['CLOUDSTACK_KEY'] = '7VKtnRKKuq9W2B9jyN2tVKzzJVMkFAzKwN89LfaHvf4TbsiktT2OvfM-24sslxLBUJE52UUNdzQ6-ggKu0GNWQ'
os.environ['CLOUDSTACK_SECRET'] = '-wynROROSi2IHTflvGfmzfPDaEy1OCln7zrohP9KOo5qt45OLNmVSLnwQ6b915oI8qH3SWb8-Au-Yxwx9G5C3g'
os.environ['CLOUDSTACK_VERIFY'] = '/home/rafael/Documents/VTKNet/VDC_HOME/pvz3/.ca.crt'

api_config = read_config()
cs = CloudStack(**api_config)

default_filter = {
    'fetch_list': True
}

inventory_j2_template = Template(INVENTORY_NORMALIZATION_J2)

def query_api( command, **args):
    res = getattr(cs, command)(**args)
    if 'errortext' in res:
        raise CloudStackException(res['errortext'])
    return res


class MyTestCase(unittest.TestCase):

    def test_get_vm_list(self):
        instances = query_api('listVirtualMachines', **default_filter)
        template = Template('{{instances.nic}}')
        result = template.render(instances=instances)
        pass

    def test_transform_vm_data(self):
        instance = query_api('listVirtualMachines', **default_filter)[0]
        instance = inventory_j2_template.render(instance=instance)
        instance = yaml.load(instance)['instance']
        self.assertTrue('name' in instance)

    def test_client_data(self):
        user = query_api('getUser', userapikey=admin['apikey'] )
        pass

    def test_get_zone_id(self):
        zones = query_api('listZones', fetchList=True)
        for zone in zones['zone']:
            if 'z1' in [zone['id'], zone['name']]:
                pass
        vpcs = query_api('listVPCs', fetchList=True)
        projects = query_api('listProjects', **default_filter)
        domains = query_api('listDomains', fetchList=True)
        pass

if __name__ == '__main__':
    unittest.main()
