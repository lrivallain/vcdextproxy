# -*- coding: utf-8 -*-

"""An AMQP to REST proxy for VMware vCloud Director Extensions.
"""

__author__ = """Ludovic Rivallain"""
__email__ = 'ludovic.rivallain@gmail.com'
__version__ = '0.1.0'

import logging
import sys
if sys.version_info < (3, 6):
    raise Exception('vcdextproxy requires Python versions 3.6 or later.')

# Import all
# from vcdextproxy.api_extension import RestApiExtension
# from vcdextproxy.rest_worker import RESTWorker
# from vcdextproxy.amqp_worker import AMQPWorker
# from vcdextproxy import configuration
# from vcdextproxy import utils

# name the logger for the current module
logger = logging.getLogger(__name__)
