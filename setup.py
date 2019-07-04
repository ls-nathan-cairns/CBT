#!/usr/bin/env python3

from setuptools import setup

setup(name='cbt',
      description='Generating code using machine learning',
      author='Buster & Nathan',
      packages=['cbt'],
      install_requires=[
            'staticfg',
            'networkx',
            'graphviz',
            'pydot',
            'comment-filter'
      ],
      dependency_links=[
            'https://github.com/codeauroraforum/comment-filter/tarball/master#egg=comment-filter-v1.0.0',
            'https://github.com/Buster-Darragh-Major/staticfg/tarball/master#egg=staticfg-0.9.5'
      ])
