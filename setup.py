# -*- coding: utf-8 -*-

import os.path
from setuptools import setup, find_packages

version = '0.1.0'

requirements = []
with open(os.path.join(os.path.dirname(__file__), 'requirements.txt')) as fp:
    requirements = [req.strip() for req in fp.readlines()]

setup(name='pyrql',
      version=version,
      description="RQL parsing and query generator",
      packages=find_packages(exclude=['tests']),
      zip_safe=False,
      install_requires=requirements,
      )
