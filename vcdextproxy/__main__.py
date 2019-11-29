#!/usr/bin/env python
"""Main script to run a proxy that handle vCD extension AMQP messages.
"""
import signal
import sys
import os
from kombu import Connection
from vcdextproxy import AMQPWorker
from vcdextproxy.configuration import configure_logger, read_configuration, conf
from vcdextproxy.utils import signal_handler, vcdextproxy_excepthook, logger


def main():
    """Execute the proxy worker.
    """
    # managed unhandled Exceptions
    sys.excepthook = vcdextproxy_excepthook

    # Import configuration for tests
    read_configuration()

    # Setup logger
    try:
        configure_logger()
    except Exception:
        logger.exception("Cannot configure the logger. Ensure settings are correct.")
        exit(-1)

    # start
    logger.info("Starting the vCD Extension Proxy service")

    # bind sigint signal to a signal handler method
    signal.signal(signal.SIGINT, signal_handler)

    # disable tracebacks in kombu
    os.environ['DISABLE_TRACEBACKS'] = "1"

    logger.info("Connecting to the RabbitMQ server...")
    amqp_url = f"amqp://{conf('global.amqp.username')}:{conf('global.amqp.password')}"
    amqp_url += f"@{conf('global.amqp.host')}:{conf('global.amqp.port')}/{conf('global.amqp.vhost')}"
    if conf('global.amqp.ssl'):
        amqp_url += "?ssl=1"
    logger.debug(f"RabbitMQ server URI: {amqp_url}")
    with Connection(amqp_url, heartbeat=4) as conn:
        # Start dispatcher service
        logger.info("Dispatcher service creation")
        dispatch = AMQPWorker(conn)
        logger.debug("Starting the dispatcher service...")
        dispatch.run()


if __name__ == '__main__':
    main()
