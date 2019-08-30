"""An AMQP to REST proxy for VMware vCloud Director Extensions.

.. moduleauthor:: Ludovic Rivallain <ludovic.rivallain+vcdextproxy --> gmail.com>
"""

import sys
if sys.version_info < (3, 6):
    raise Exception('vcdextproxy requires Python versions 3.6 or later.')

__all__ = [
    'rest_worker',
    'amqp_worker',
    'utils',
    'configuration'
]

__version__="0.0.1"
"""Define the version of the package.
"""