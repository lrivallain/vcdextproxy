"""An AMQP to REST proxy for VMware vCloud Director Extensions.

.. moduleauthor:: Ludovic Rivallain <ludovic.rivallain+vcdextproxy --> gmail.com>
"""

import sys
if sys.version_info < (3, 6):
    raise Exception('vcdextproxy requires Python versions 3.6 or later.')

# Import all
from vcdextproxy.rest_worker import RESTWorker
from vcdextproxy.amqp_worker import AMQPWorker
from vcdextproxy.api_extension import RestApiExtension
from vcdextproxy import configuration
from vcdextproxy import utils

__version__="0.0.1"
"""Define the version of the package.
"""

# name the logger for the current module
import logging
logger = logging.getLogger(__name__)