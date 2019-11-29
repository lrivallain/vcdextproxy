#!/usr/bin/env python
"""RestApiExtension defines the settings of a single REST API extension unit for vCD.
"""
from kombu import Exchange, Queue
import json
from requests.auth import HTTPBasicAuth
from vcdextproxy.configuration import conf
from vcdextproxy.utils import logger
from vcdextproxy.vcd_utils import VcdSession, get_vcd_rights


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

    def get_reference_right(self):
        """Get the ID of the reference right set in the configuration
        """
        if not self.conf('vcloud.reference_right', False):
            return False
        else:
            for instance_right in get_vcd_rights(self.name):
                if instance_right['name'] == self.conf('vcloud.reference_right'):
                    return instance_right['id']
            # If not already found: error
            self.log(
                'error',
                f"Invalid reference right `{self.conf('vcloud.reference_right')}` configured for the extension."
            )
            # Return a fake ID to force errors when checking user's rights
            return "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    def initialize_on_vcloud(self):
        """Check/initialize the deployment of extension on vCloud.
        """
        self.log('info', 'Checking the initialization status of extension in vCloud.')
        if not (
            self.conf('vcloud.api_extension.namespace') and
            self.conf('vcloud.api_extension.exchange') and
            self.conf('vcloud.api_extension.routing_key')
        ):
            self.log('warning', 'Missing items in configuration to make the initialization check-up. Ignoring.')
            return
        vcd_sess = VcdSession(
            hostname=conf('global.vcloud.hostname'),
            username=conf('global.vcloud.username'),
            password=conf('global.vcloud.password'),
            api_version=conf('global.vcloud.api_version'),
            ssl_verify=conf('global.vcloud.ssl_verify', True),
            logger_prefix=self.name
        )
        qf = f"name%3D%3D{self.name}%3Bnamespace%3D%3D{self.conf('vcloud.api_extension.namespace')}"
        query_res = vcd_sess.query(type="adminService", filter=qf)
        xml_data = self.generate_xml4ext()
        if not query_res:
            self.log('warning', "This extension is not (yet) declared on vCloud.")
            current_ext_on_vcd = None
        else:
            current_ext_on_vcd = query_res[0]
        if current_ext_on_vcd and self.conf('vcloud.api_extension.force_redeploy'):
            current_ext_on_vcd = self.unregister_extension(
                vcd_sess, xml_data, current_ext_on_vcd.get("href"))
        if (not current_ext_on_vcd) or self.conf('vcloud.api_extension.force_redeploy'):
            current_ext_on_vcd = self.register_extension(vcd_sess, xml_data)
            if not current_ext_on_vcd:
                return  # error already logged
        if not current_ext_on_vcd.get('enabled'):
            self.log('warning', "This extension is not enabled on vCloud.")

    def register_extension(self, vcd_sess: VcdSession, xml_data: str):
        """Register this extension in vCloud Director.

        Args:
            vcd_sess (VcdSession): the vcloud session context.
            xml_data (str): XML data for the extension.
        """
        self.log('info', f"Registering extension {self.name} as a new vCD API extension.")
        ext_data = vcd_sess.post(
            "/api/admin/extension/service",
            data=xml_data,
            content_type="application/vnd.vmware.admin.service+xml",
            full_return=True
        )
        if ext_data.status_code >= 300:
            self.log(
                'error',
                f"Error HTTP/{ext_data.status_code} when registering the new extension. Please check your settings."
            )
            self.log('debug', ext_data.content)
            return None
        else:
            self.log('trivia', json.dumps(json.loads(ext_data.content), indent=2))
            return json.loads(ext_data.content)

    def unregister_extension(self, vcd_sess: VcdSession, xml_data: str, ext_href: str):
        """Unregister this extension from vCloud Director.

        Args:
            vcd_sess (VcdSession): the vcloud session context.
            xml_data (str): XML data for the extension.
            ext_href (str): URI for the extension in API
        """
        self.log('info', f"Unregistering extension {self.name} from vCD API extension(s).")
        self.log('debug', f"Disable extension {self.name} from vCD API extension(s).")
        self.update_extension(
            vcd_sess,
            xml_data.replace("<vmext:Enabled>true", "<vmext:Enabled>false"),
            ext_href
        )
        ext_href = "/api/" + ext_href.split('/api/')[1]  # remove hostname part
        ext_data = vcd_sess.delete(
            ext_href,
            full_return=True
        )
        if ext_data.status_code >= 300:
            self.log(
                'error',
                f"Error HTTP/{ext_data.status_code} when registering the new extension. Please check your settings."
            )
            self.log('debug', ext_data.content)
            return None
        else:
            self.log('trivia', ext_data.content)
            return None

    # TODO : not updating ApiFilter...
    def update_extension(self, vcd_sess: VcdSession, xml_data: str, ext_href: str):
        """Update an existing extension in vCloud Director.

        Args:
            vcd_sess (VcdSession): the vcloud session context.
            xml_data (str): XML data for the extension.
            ext_href (str): URI for the extension in API
        """
        self.log('info', f"Updating extension {self.name} vCD API extension.")
        ext_href = "/api/" + ext_href.split('/api/')[1]  # remove hostname part
        ext_data = vcd_sess.put(
            ext_href,
            data=xml_data,
            content_type="application/vnd.vmware.admin.service+xml",
            full_return=True)
        if ext_data.status_code >= 300:
            self.log(
                'error',
                f"Error HTTP/{ext_data.status_code} when updating the new extension. Please check your settings."
            )
            self.log('debug', ext_data.content)
            return None
        else:
            self.log('trivia', json.dumps(json.loads(ext_data.content), indent=2))
            return json.loads(ext_data.content)

    def generate_xml4ext(self):
        """Generate the XML for the extension registering/update.
        """
        # prepare XML declaration
        xml_api_filters = ""
        for af in self.conf('vcloud.api_extension.api_filters'):
            xml_api_filters += f"""<vmext:ApiFilter>
        <vmext:UrlPattern>{af}</vmext:UrlPattern>
    </vmext:ApiFilter>"""
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<vmext:Service xmlns:vmext="http://www.vmware.com/vcloud/extension/v1.5"
                xmlns="http://www.vmware.com/vcloud/v1.5" name="{self.name}">
<vmext:Namespace>{self.conf('vcloud.api_extension.namespace')}</vmext:Namespace>
<vmext:Enabled>true</vmext:Enabled>
<vmext:RoutingKey>{self.conf('vcloud.api_extension.routing_key')}</vmext:RoutingKey>
<vmext:Exchange>{self.conf('vcloud.api_extension.exchange')}</vmext:Exchange>
<vmext:ApiFilters>
    {xml_api_filters}
</vmext:ApiFilters>
</vmext:Service>"""
        self.log('trivia', xml_data)
        return xml_data
