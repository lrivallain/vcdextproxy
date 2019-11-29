#!/usr/bin/env python
"""Define here some usefull functions
"""
import sys
import traceback

import logging
logger = logging.getLogger()

# managed unhandled Exceptions


def vcdextproxy_excepthook(type, value, tb):
    """Print the unhandled exceptions.
    """
    logger.error(f"Unhandled exception {type}: {value}")
    logger.warning(f"################### Traceback ###################")
    traceback.print_tb(tb)
    logger.warning(f"############### End of Traceback ################")

# Manage clean exit


def signal_handler(signal, frame):
    """Handle a Keyboard Interrupt to leave rabbitMQ connection.
    """
    sys.stdout.write('\b\b\r')  # hide the ^C
    logger.info("SIGINT signal catched -> Exiting...")
    sys.exit(0)
