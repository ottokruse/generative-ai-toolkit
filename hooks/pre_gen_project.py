#!/usr/bin/env python3

import re
import sys

PYTHON_CLASSNAME_REGEX = r"^[_a-zA-Z][_a-zA-Z0-9]*$"
DIRNAME_REGEX = r"^[\w\-. ]+$"

agent_name = "{{ cookiecutter.agent_name }}"
package_name = "{{ cookiecutter.package_name }}"

if not re.match(DIRNAME_REGEX, package_name):
    print(f"ERROR: {package_name} is not a valid directory name")
    sys.exit(1)

if not re.match(PYTHON_CLASSNAME_REGEX, agent_name):
    print(f"ERROR: {agent_name} is not a valid Python class name")
    sys.exit(1)
