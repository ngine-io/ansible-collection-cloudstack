#!/usr/bin/env bash
set -eux
env

# Required to differentiate between Python 2 and 3 environ
PYTHON=${ANSIBLE_TEST_PYTHON_INTERPRETER:-python}

# TODO: the test environment is bit setup when running this integration test on its own.
${PYTHON} -m pip install cs

CLOUDSTACK_CONFIG=$(pwd)/cloudstack.ini
export CLOUDSTACK_CONFIG

# TODO: why is it looking for cloudstack conf section?
ansible-playbook playbooks/cloudstack-inventory-test.yml "$@"

ansible-inventory --list -i test.cloudstack.yml "$@"

