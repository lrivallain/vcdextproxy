# -*- coding: utf-8 -*-

"""An AMQP to REST proxy for VMware vCloud Director Extensions.
"""

__author__ = """Ludovic Rivallain"""
__email__ = 'ludovic.rivallain@gmail.com'
__version__ = '0.1.1'

import logging
import sys
if sys.version_info < (3, 6):
    raise Exception('vcdextproxy requires Python versions 3.6 or later.')

# Import all submodules
from vcdextproxy.api_extension import RestApiExtension  # noqa: E402, F401
from vcdextproxy.rest_worker import RESTWorker  # noqa: E402, F401
from vcdextproxy.amqp_worker import AMQPWorker  # noqa: E402, F401
from vcdextproxy import configuration  # noqa: E402, F401
from vcdextproxy import utils  # noqa: E402, F401

# name the logger for the current module
logger = logging.getLogger(__name__)
