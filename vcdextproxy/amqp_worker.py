#!/usr/bin/env python
"""The AMQP worker is in charge of dealing with AMQP messages.
"""

import base64
import json
from amqp.exceptions import PreconditionFailed
from kombu import Exchange, Queue
from kombu.mixins import ConsumerMixin
from kombu.utils.debug import setup_logging as kombu_setup_logging
from threading import BoundedSemaphore
from vcdextproxy.configuration import conf
from vcdextproxy.utils import logger
from vcdextproxy import RestApiExtension, RESTWorker


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
        self.registered_extensions = {}  # keep extensions
        # Limit threads number #13
        self.thread_limiter = BoundedSemaphore(value=conf('global.max_threads', 10))
        self.nb_requests_managed = 0

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
            extension = RestApiExtension(extension_name)
            routing_key = extension.conf('amqp.routing_key')
            if routing_key in self.registered_extensions.keys():
                # critical case: duplicate routing_key in configuration
                logger.critical(f"Duplicate routing_key '{routing_key}' for multiple extensions.")
                return None
            queue = extension.get_queue()
            if queue:
                try:
                    consumers.append(
                        Consumer(
                            queues=[queue],
                            callbacks=[self.process_task]
                        )
                    )
                except PreconditionFailed:
                    logger.exception("Precondition error: Verify AMQP settings for {extension.name}")
                except Exception:
                    logger.exception("Unmanaged error detected.")
                self.registered_extensions[routing_key] = extension
                extension.log('info', f"New extension is registred.")
        logger.info("All extensions are now registred. Listening for incoming messages...")
        return consumers

    def process_task(self, body, message):
        """Process a single message on receive.

        Args:
            body (str): JSON message body as a string.
            message (str): JSON message metadata as a string.
        """
        self.thread_limiter.acquire()
        logger.trivia(f"Available threads to manage the request: {self.thread_limiter._value}")
        try:
            message.ack()
        except ConnectionResetError:
            logger.error("Listener: ConnectionResetError: message may not have been acknowledged...")
        logger.debug("Listener: New message received in MQ")
        routing_key = message.delivery_info['routing_key']
        extension = self.registered_extensions.get(routing_key)
        if not extension:
            logger.error(f"Listener: Cannot found the configuration data for the routing_key {routing_key}")
            message.requeue()  # reject and sent it back to server
            return  # Do nothing
        extension.log('info', f"Listener: Message with routing_key '{routing_key}' is received.")
        # Parsing JSON
        try:
            extension.log('debug', "Listener: Loading body as a JSON content...")
            json_payload = json.loads(body)
            extension.log('debug', "Listener: Body of message was successfully load as JSON.")
        except ValueError:
            extension.log('warning', f"Listener: Invalid JSON data received: rejecting the message\n{body}")
            return
        # Getting the correct worker
        extension.log('debug', "Listener: Processing request message in a new thread...")
        # Limit threads number #13
        try:
            thread = RESTWorker(
                extension=extension,
                message_worker=self,
                data=json_payload,
                message=message
            )
            thread.start()
        except Exception as e:
            extension.log('error', f"Listener: Task raised exception: {str(e)}", exc_info=1)
            self.thread_limiter.release()

    def publish(self, data, properties):
        """Publish a message through the current connection.

        Args:
            data (str): JSON message body as a string.
            properties (str): JSON message metadata as a string.
        """
        routing_key = properties.get('routing_key')
        if not routing_key:
            logger.error(f"Publisher: Missing original routing_key in the reply message properties")
            return  # Do nothing
        extension = self.registered_extensions.get(routing_key)
        if not extension:
            logger.error(
                f"Publisher: Cannot found the configuration data for the routing_key {routing_key}"
            )
            self.thread_limiter.release()
            return  # Do nothing
        extension.log(
            'info',
            f"Publisher: Reply with routing_key {routing_key} is received. Sending a message to MQ...."
        )
        rqueue = Queue(
            properties.get('reply_to'),
            Exchange(
                properties.get("replyToExchange"),
                'direct',
                durable=True,
                no_declare=True  # we consider it as already available
            ),
            routing_key=properties.get('reply_to'),
            no_declare=True
        )
        if properties.get("encode", True):
            rsp_body = (base64.b64encode(data.encode('utf-8'))).decode()
        else:
            rsp_body = (base64.b64encode(data)).decode()  # raw data
        rsp_msg = {
            'id': properties.get('id', None),
            'headers': {
                'Content-Type': properties.get(
                    "Content-Type", "application/*+json;version=31.0"  # default
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
                retry=True,
                expiration=10000  # 10 seconds
            )
            extension.log('info', "Publisher: Response sent to MQ")
        except ConnectionResetError:
            extension.log('error', "Publisher: ConnectionResetError: message may be not sent...")
        finally:
            self.thread_limiter.release()
        self.nb_requests_managed += 1
