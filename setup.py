#!/usr/bin/env python
# Copyright @ 2015 EMC Corporation All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
import re
import os
import glob

try:
    import multiprocessing  # noqa
except ImportError:
    pass
import setuptools


def load_version(filename):
    version = None
    with open(filename) as verfile:
        for line in verfile:
            version = re.search('\d+.\d+.\d+', line)
            if version is not None:
                version = version.group()
                break
        if version is None:
            version = "0.0.0"
    return version


def load_requirements(filename):
    requirements = []
    with open(filename) as reqfile:
        for line in reqfile:
            if not line.startswith("#"):
                line = line.strip()
                requirements.append(line)
    return requirements


data_files = []
for x in os.walk('data'):
    data_files.append(
        ('infrasim/' + '/'.join(os.path.split(x[0])),
         glob.glob(os.path.join(x[0], '*.*'))
        )
    )
for x in os.walk('template'):
    data_files.append(
        ('infrasim/' + '/'.join(os.path.split(x[0])),
         glob.glob(os.path.join(x[0], '*'))
        )
    )

setuptools.setup(
    name='infrasim-compute',
    description='Bare-metal server simulator',
    version=load_version("template/version.yml"),
    author='EMC',
    author_email='infrasim.dev@emc.com',
    license='Apache 2.0',
    url='https://github.com/InfraSIM/infrasim-compute',
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    install_requires=load_requirements("requirements.txt"),
    scripts=['bin/infrasim-init', 'bin/infrasim-main', 'bin/ipmi-console',
             'package_install.sh'],
    data_files=data_files,
    )
