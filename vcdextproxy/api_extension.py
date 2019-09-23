#!/usr/bin/env python
"""RestApiExtension defines the settings of a single REST API extension unit for vCD.
"""
from kombu import Exchange, Queue
from vcdextproxy.configuration import conf
from vcdextproxy.utils import logger


class RestApiExtension:
    """Define an extension object with its settings
    """

    def init(self, extension_name):
        """Initialize an extension object

        Args:
            extension_name (str): Name of the extension
        """
        self.name = extension_name
        self.conf = f'extensions.{extension_name}'

    def log(self, level, message, *args, **kwargs):
        """Log a information about this extension by adding a prefix

        Args:
            level (str): Log level for the information
            message (str): Message to log
        """
        _message = f"[{self.name}] {str(message)}"
        try:
            getattr(logger, level)(_message)  #, args, kwargs)
        except AttributeError as e:
            self.log("error", f"Invalid log level {level} used: please fix in code.")
            self.log("debug", message, *args, **kwargs)  # loop with a sure status

    def get_url(self, uri_path, query_string=None):
        """Return URL for this extension

        Args:
            uri_path (str): original URI path from the request
            query_string (str): query parameters string

        Returns:
            str: URL to use on the backend server.
        """
        full_req_path = conf(f"{self.conf}.backend.endpoint")
        # Change the requested URI before sending to backend #14
        if conf(f"{self.conf}.backend.uri_replace", False):
            pattern = conf(f"{self.conf}.backend.uri_replace.pattern", "")
            by = conf(f"{self.conf}.backend.uri_replace.by", "")
            self.log('debug', f"URI replacement: {pattern} >> {by}")
            uri_path = uri_path.replace(pattern, by)
        full_req_path += uri_path
        if query_string:
            full_req_path += "?" + query_string
        return full_req_path

    def get_conf(self, item, default=None):
        """Returns configuration value for this extension.

        Returns:
            any: The value for the requested item.
        """
        return conf(f"{self.conf}.{item}", default)

    def get_extension_auth(self):
        """Get the auth object if requested by extension.

        Returns:
            HTTPBasicAuth: Auth context.
        """
        if conf(f"{self.conf}.backend.auth", False):
            return HTTPBasicAuth(
                conf(f"{self.conf}.backend.auth.username", ""),
                conf(f"{self.conf}.backend.auth.password", ""),
            )
        return None

    def get_queue(self):
        """Return a Queue subscribtion for the extension
        """
        routing_key = self.conf('amqp.routing_key')
        self.log('info', f"Initializating a new listener.")
        self.log('debug',
            f"Preparing a new Exchange object: " + self.conf('amqp.exchange.name'))
        exchange = Exchange(
            name=self.conf('amqp.exchange.name'),
            type=self.conf('amqp.exchange.type', 'topic'),
            durable=self.conf('amqp.exchange.durable', True),
            no_declare=self.conf('amqp.no_declare', True)
        )
        self.log('debug', f"Preparing a new Queue object: " + self.conf('amqp.queue.name'))
        queue = Queue(
            name=self.conf('amqp.queue.name'),
            exchange=exchange,
            routing_key=routing_key,
            no_declare=self.conf('amqp.no_declare', True),
            message_ttl=self.conf('amqp.queue.message_ttl', 30)
        )
        self.log('debug', f"Adding a new process task as callback for incoming messages")
        return queue