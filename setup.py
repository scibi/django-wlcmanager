#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

import wlcmanager

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = wlcmanager.__version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='django-wlcmanager',
    version=version,
    description="""Django app to manage part of Juniper WLC configuration.""",
    long_description=readme + '\n\n' + history,
    author='Patryk Ściborek',
    author_email='patryk@sciborek.com',
    url='https://github.com/scibi/django-wlcmanager',
    packages=[
        'wlcmanager',
    ],
    include_package_data=True,
    install_requires=[
    ],
    dependency_links=['https://github.com/Juniper/py-jnpr-wlc/tarball/master#egg=py-jnpr-wlc-1.0'],
    license="BSD",
    zip_safe=False,
    keywords='django-wlcmanager',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
)
