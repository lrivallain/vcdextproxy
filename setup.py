from distutils.core import setup
import setuptools
import vcdextproxy

try:
    with open("README.md", "r") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "" # empty
except Exception as e:
    raise e

setup(
    name='vcdextproxy',
    version=vcdextproxy.__version__,
    author="Ludovic Rivallain",
    author_email='ludovic.rivallain+vcdextproxy@gmail.com',
    packages=setuptools.find_packages(),
    description="An AMQP to REST proxy for VMware vCloud Director Extensions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "kombu",
        "coloredlogs",
        "requests",
        "cachetools"
    ],
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8', 'Operating System :: Unix',
        'Operating System :: POSIX :: Linux',
        "License :: OSI Approved :: MIT License", "Environment :: Console"
    ],
    entry_points={
        'console_scripts': [
            'vcdextproxy=vcdextproxy.__main__:main',
        ],
    })