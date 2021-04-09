#!/usr/bin/env bash
set -eux
env

# Required to differentiate between Python 2 and 3 environ
PYTHON=${ANSIBLE_TEST_PYTHON_INTERPRETER:-python}

# TODO: the test environment is not setup when running this integration test on its own.
${PYTHON} -m pip install cs

# TODO: why is it looking for cloudstack conf section?
ansible-playbook playbooks/basic-configuration.yml "$@"

# Configure simulator endpoint
source cloudstack.env

ansible-playbook playbooks/instance-inventory-test.yml "$@"

ansible-inventory --list -i cloudstack-instances.yml

