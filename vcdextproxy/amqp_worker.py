#!/usr/bin/env python
"""The AMQP worker is in charge of dealing with AMQP messages.
"""

import base64
import sys
import json
import logging
from kombu import Exchange, Queue, Connection
from kombu.mixins import ConsumerMixin
from kombu.utils.debug import setup_logging as kombu_setup_logging
from .rest_worker import RESTWorker
from .configuration import conf


# name the logger for the current module
logger = logging.getLogger(__name__)


# def amqp_errback(error, interval):
#     """Provide custom error callback on amqp connection status

#     Args:
#         error (Exception): The raised error
#         interval (int): Time interval between retries
#     """
#     logger.error(f"Error: {error}", exc_info=1)
#     logger.info(f"Retry in {interval} seconds.")


class AMQPWorker(ConsumerMixin):
    """kombu.ConsumerMixin based object.

    A kombu.ConsumerMixin based object that handle the messages
    received in the RabbitMQ queue and process them. When proceed,
    an reply is sent back.
    """

    def __init__(self, connection):
        """Init a new ConsumerMixin object.

        Args:
            connection (kombu.Connection): The Kombu Connection object context.
        """
        self.connection = connection
        # Reduce logging from amqp module
        kombu_setup_logging(loglevel='INFO', loggers=['amqp'])
        self.registered_extensions = {} # keep extensions
        self.registered_workers = {}  # keep routing keys

    def get_consumers(self, Consumer, channel):
        """Return the consumer objects.

        Args:
            Consumer (kombu..messaging.Consumer): Current consumer object.
            channel (str): Incoming channel for messages (unused).

        Returns:
            [kombu.messaging.Consumer]: A list of consumers with callback to local task.
        """
        consumers = []
        for extension_name in conf('extensions'):
            extension_conf_path = 'extensions.' + extension_name
            routing_key = conf(extension_conf_path + '.amqp.routing_key')
            if routing_key in self.registered_workers.keys():
                # critical case: duplicate routing_key in configuration
                logger.critical(f"Duplicate routing_key {routing_key} for multiple extensions.")
                return
            logger.info(f"Extension {extension_name} - Initializating a new listener.")
            logger.debug(f"Extension {extension_name} - Preparing a new Exchange object: " + conf(extension_conf_path + '.amqp.exchange.name'))
            exchange = Exchange(
                name=conf(extension_conf_path + '.amqp.exchange.name'),
                type=conf(extension_conf_path + '.amqp.exchange.type', 'topic'),
                durable=conf(extension_conf_path + '.amqp.exchange.durable', True),
                no_declare=conf(extension_conf_path + '.amqp.declare', True)
            )
            logger.debug(f"Extension {extension_name} - Preparing a new Queue object: " + conf(extension_conf_path + '.amqp.queue.name'))
            queue = Queue(
                name=conf(extension_conf_path + '.amqp.queue.name'),
                exchange=exchange,
                routing_key=routing_key,
                no_declare=conf(extension_conf_path + '.amqp.declare', True),
                message_ttl=conf(extension_conf_path + '.amqp.queue.message_ttl', 30000)
            )
            logger.debug(f"Extension {extension_name} - Adding a new process task as callback for incoming messages")
            consumers.append(
                Consumer(
                    queues=[queue],
                    callbacks=[self.process_task]
                )
            )
            self.registered_extensions[routing_key] = extension_name
            logger.info(f"Extension {extension_name} - New extension is registred.")
        return consumers

    def process_task(self, body, message):
        """Process a single message on receive.

        Args:
            body (str): JSON message body as a string.
            message (str): JSON message metadata as a string.
        """
        logger.info("Listener: New message received in MQ")
        # Parsing JSON
        try:
            json_payload = json.loads(body)
        except ValueError:
            logger.error("Listener: Invalid JSON data received: ignoring the message\n{body}")
            return
        # Acknowledge it
        try:
            message.ack()
        except ConnectionResetError:
            logger.error("Listener: ConnectionResetError: message may not have been acknowledged...")
        # Getting the correct worker
        logger.debug("Listener: Processing request message in a new thread...")
        routing_key = message.properties['routing_key']
        extension = self.registered_extensions.get(routing_key)
        if not extension:
            logger.error(f"Listener: Cannot found the configuration data for the routink_key {routing_key}")
            return # Do nothing
        try:
            thread = RESTWorker(
                extension = extension,
                message_worker = self,
                data = json_payload,
                message = message
            )
            thread.start()
        except Exception as e:
            logger.error(f"Listener: Task raised exception: {str(e)}")

    def publish(self, data, properties):
        """Publish a message through the current connection.

        Args:
            data (str): JSON message body as a string.
            properties (str): JSON message metadata as a string.
        """
        logger.debug("Publisher: Sending a message to MQ...")
        rqueue = Queue(
            properties.get('reply_to'),
            Exchange(
                properties.get("replyToExchange"),
                'direct',
                durable=True,
                no_declare=True # we consider it as already available
            ),
            routing_key=properties.get('reply_to'),
            no_declare=True
        )
        if properties.get("encode", True):
            rsp_body = (base64.b64encode(data.encode('utf-8'))).decode()
        else:
            rsp_body = (base64.b64encode(data)).decode() # raw data
        rsp_msg = {
            'id': properties.get('id', None),
            'headers': {
                'Content-Type': properties.get(
                    "Content-Type", "application/*+json;version=31.0" # default
                ),
                'Content-Length': len(data)
            },
            'statusCode': properties.get("statusCode", 200),
            'body': rsp_body
        }
        try:
            self.connection.Producer().publish(
                rsp_msg,
                correlation_id=properties.get('correlation_id'),
                routing_key=rqueue.routing_key,
                exchange=rqueue.exchange,
                retry = True,
                expiration = 10000 # 10 seconds
            )
            logger.info("Publisher: Response sent to MQ")
        except ConnectionResetError:
            logger.error("Publisher: ConnectionResetError: message may be not sent...")