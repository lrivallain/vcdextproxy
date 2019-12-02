#!/usr/bin/env python
"""RestApiExtension defines the settings of a single REST API extension unit for vCD.
"""
from kombu import Exchange, Queue
import json
import sys
from requests.auth import HTTPBasicAuth
from vcdextproxy.configuration import conf
from vcdextproxy.utils import logger
from vcdextproxy.vcd_utils import list_rights_available_in_vcd, login_as_system_admin
from pyvcloud.vcd.api_extension import APIExtension


class RestApiExtension:
    """Define an extension object with its settings
    """

    def __init__(self, extension_name):
        """Initialize an extension object

        Args:
            extension_name (str): Name of the extension
        """
        self.name = extension_name
        self.conf_path = f'extensions.{extension_name}'
        self.ref_right_id = self.get_reference_right()
        self.initialize_on_vcloud()

    def log(self, level, message, *args, **kwargs):
        """Log a information about this extension by adding a prefix

        Args:
            level (str): Log level for the information
            message (str): Message to log
        """
        _message = f"[{self.name}] {str(message)}"
        try:
            getattr(logger, level)(_message)
        except AttributeError:
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
        full_req_path = self.conf(f"backend.endpoint")
        # Change the requested URI before sending to backend #14
        if self.conf(f"backend.uri_replace", False):
            pattern = self.conf(f"backend.uri_replace.pattern", "")
            by = self.conf(f"backend.uri_replace.by", "")
            self.log('debug', f"URI replacement: {pattern} >> {by}")
            uri_path = uri_path.replace(pattern, by)
        full_req_path += uri_path
        if query_string:
            full_req_path += "?" + query_string
        return full_req_path

    def conf(self, item, default=None):
        """Returns configuration value for this extension.

        Returns:
            any: The value for the requested item.
        """
        return conf(f"{self.conf_path}.{item}", default)

    def get_extension_auth(self):
        """Get the auth object if requested by extension.

        Returns:
            HTTPBasicAuth: Auth context.
        """
        if self.conf(f"backend.auth", False):
            return HTTPBasicAuth(
                self.conf(f"backend.auth.username", ""),
                self.conf(f"backend.auth.password", ""),
            )
        return None

    def get_queue(self):
        """Returns a Queue subscribtion for the extension
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

    def get_reference_right(self):
        """Get the ID of the reference right set in the configuration
        """
        if not self.conf('vcloud.reference_right', False):
            return False
        else:
            for instance_right in list_rights_available_in_vcd(self.name):
                if instance_right['name'] == self.conf('vcloud.reference_right'):
                    return instance_right['href'].split('/')[-1]
            # If not already found: error
            self.log(
                'error',
                f"Invalid reference right `{self.conf('vcloud.reference_right')}` configured for the extension."
            )
            # Return a fake ID to force errors when checking user's rights
            return "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    def initialize_on_vcloud(self):
        """Check and/register the extension on vCloud.
        """
        self.log('info', 'Checking the initialization status of extension in vCloud.')
        if not (
            self.conf('vcloud.api_extension.namespace') and
            self.conf('vcloud.api_extension.exchange') and
            self.conf('vcloud.api_extension.routing_key')
        ):
            self.log('warning', 'Missing items in configuration to make the initialization check-up. Ignoring.')
            return
        client = login_as_system_admin()
        ext_manager = APIExtension(client)
        try:
            current_ext_on_vcd = ext_manager.get_extension_info(
                self.name,
                namespace=self.conf('vcloud.api_extension.namespace'))
            self.log('info', 'Extension is already registered on vCloud')
        except MissingRecordException:
            self.log('warning', "This extension is not (yet) declared on vCloud.")
            current_ext_on_vcd = None
        except MultipleRecordsException:
            self.log('error', "Multiple extensions found with same name and namespace")
            sys.exit(-1)
        # Force a fresh redeploy of the full extension (Warning: be carrefull, ID will change !)
        if current_ext_on_vcd and self.conf('vcloud.api_extension.force_redeploy', False):
            ext_manager.delete_extension(
                self.name,
                namespace=self.conf('vcloud.api_extension.namespace'))
            self.log('info', 'Extension is unregistered on vCloud')
            current_ext_on_vcd = None
        # Only update an existing extension (Warning: does not update the API filters/patterns!)
        if current_ext_on_vcd and self.conf('vcloud.api_extension.auto_update', False):
            current_ext_on_vcd = ext_manager.update_extension(
                self.name,
                namespace=self.conf('vcloud.api_extension.namespace'),
                routing_key=self.conf('vcloud.api_extension.routing_key'),
                exchange=self.conf('vcloud.api_extension.exchange'))
            self.log('info', 'Extension is updated on vCloud')
        # Register a new extension
        if not current_ext_on_vcd:
            ext_manager.add_extension(
                self.name,
                namespace=self.conf('vcloud.api_extension.namespace'),
                routing_key=self.conf('vcloud.api_extension.routing_key'),
                exchange=self.conf('vcloud.api_extension.exchange'),
                patterns=self.conf('vcloud.api_extension.api_filters'))
            self.log('info', 'Extension is registered on vCloud')
        # Ensure to enable it
        ext_manager.enable_extension(self.name,
                namespace=self.conf('vcloud.api_extension.namespace'),
                enabled=True)
        self.log('info', 'Extension is enabled on vCloud')
