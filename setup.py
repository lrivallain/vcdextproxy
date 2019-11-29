#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "kombu",
    "coloredlogs",
    "requests",
    "cachetools",
    "PyYAML"
]

setup_requirements = [
    'pytest-runner'
]

test_requirements = [
    'pytest>=3'
]

description = "A python based proxy looking at multiple AMQP queues "
description += "for incoming requests of VMware vCloud Director's API Extensions"

setup(
    author="Ludovic Rivallain",
    author_email='ludovic.rivallain@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description=description,
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='vcdextproxy',
    name='vcdextproxy',
    packages=find_packages(include=['vcdextproxy', 'vcdextproxy.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/lrivallain/vcdextproxy',
    version='0.1.1',
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'vcdextproxy=vcdextproxy.__main__:main',
        ],
    }
)
