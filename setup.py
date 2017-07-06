# -*- coding: utf-8 -*-

import os
import re
import sys


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'test':
    try:
        __import__('pytest')
    except ImportError:
        print('pytest required.')
        sys.exit(1)

    errors = os.system('pytest')
    sys.exit(bool(errors))


with open('pyrql/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

packages = [
    'pyrql'
    ]

install = [
    'pyparsing',
    'python-dateutil',
    ]

setup(
    name='pyrql',
    version=version,
    description="RQL parsing",
    packages=packages,
    tests_require=['pytest'],
    install_requires=install,
    )
