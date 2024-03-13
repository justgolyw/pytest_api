#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-api',
    version='1.5.2',
    author='chenshuanglin',
    author_email='61067@sangfor.com',
    maintainer='chenshuanglin',
    maintainer_email='61067@sangfor.com',
    license='BSD-3',
    url='https://github.com/chenshuanglin/pytest-api',
    description='rest api test',
    long_description=read('README.rst'),
    packages=['pytest_api'],
    python_requires='>=3.6',
    install_requires=['pytest>=3.5.0', 'PyYAML>==5.3.1', 'requests', 'regex'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    entry_points={
        'pytest11': [
            'api = pytest_api.plugin',
        ],
    },
)

