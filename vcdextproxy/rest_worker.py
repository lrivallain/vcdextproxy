import base64
import json
import logging
import requests
import json
from threading import Thread
from requests.auth import HTTPBasicAuth
from .configuration import conf


# name the worker for the module
logger = logging.getLogger(__name__)


class RESTWorker(Thread):
    def __init__(self, extension, message_worker, data, message):
        Thread.__init__(self)
        self.extension_name = extension
        # enable to publish response from the worker
        self.message_worker = message_worker
        # content of the request message
        self.request = data
        # message metadata
        self.amqp_message = message
        # message headers + some extra ones
        self.headers = self.forge_headers()
        # get the current auth token
        self.token = None
        for header_key, header_value in self.headers.items():
            if header_key.lower() == "x-vcloud-authorization" or header_key.lower() == "authorization" :
                self.token = header_value

    def get_extension_auth(self):
        """Get the auth object if requested by extension.

        Returns:
            HTTPBasicAuth: Auth context.
        """
        if conf(f"extensions.{self.extension_name}.backend.auth", False):
            return HTTPBasicAuth(
                conf(f"extensions.{self.extension_name}.backend.username"),
                conf(f"extensions.{self.extension_name}.backend.password")
            )
        return None

    def forge_headers(self):
        """Returns all the headers for requests to backend

        Returns:
            dict: The headers dictionnary
        """
        # split request content from vcd context data
        vcd_data = self.request[1]
        req_data = self.request[0]
        headers = headers = req_data.get('headers', {})
        # parse information from vcd request metadata. Add them to request headers #10
        headers['org_id'] = vcd_data.get('org', '').split("urn:vcloud:org:")[1]
        headers['user_id'] = vcd_data.get('user', '').split("urn:vcloud:user:")[1]
        headers['user_rights'] = json.dumps(vcd_data.get('rights'))
        return headers

    def get_full_url(self, req_uri, query_string):
        """Get the full URL to use on backend server.

        Args:
            req_uri (str): String to append to the URL
            query_string (str): Query string part of requested URL

        Returns:
            str: The full URL to request on backend.
        """
        full_req_path = conf(f"extensions.{self.extension_name}.backend.endpoint")
        full_req_path += req_uri
        if query_string:
            full_req_path += "?" + query_string
        return full_req_path

    def pre_checks(self):
        """Run some pre-checks like checking rights.
        """
        #TODO: check rights + org membership
        return True

    def run(self):
        """Handle all messages received on the RabbitMQ Exchange.
        """
        # split request content from vcd context data
        req_data = self.request[0]
        # parse information from user request
        method = req_data.get('method', 'get').lower() # force lower to be able to use it in requests
        query_string = req_data.get('queryString', None)
        request_uri = req_data.get('requestUri', None)
        # decode request body
        body = base64.b64decode(req_data.get('body', ''))
        # search the current auth token in headers
        if not self.pre_checks():
            raise Exception("Pre check error") #TODO: Do better exceptions
        # search the appropriate requests attr
        try:
            forward_request = getattr(requests, method) # Get the requests function based on the requested method
        except AttributeError as e:
            logger.error(f"The method {method} is not supported.")
            return
        except Exception as e:
            logger.error(f"Unmanaged error raised: {str(e)}")
            raise e # raise other errors as usual
        # forward the requests to the backend
        r = forward_request(
            self.get_full_url(request_uri, query_string),
            data=body,
            auth=self.get_extension_auth(),
            headers=self.headers,
            verify=conf(f"extensions.{self.extension_name}.backend.ssl_verify", True)
        )
        # parse response
        try:
            rsp_body = r.json()
        except ValueError as e:
            rsp_body = r.text
        except Exception as e:
            logger.error(f"Unmanaged error raised: {str(e)}")
            raise e # raise other errors as usual
        # prepare reply properties
        resp_prop = {
            "id": req_data['id'],
            "accept": self.headers.get('Accept', None),
            "correlation_id": self.amqp_message.properties['correlation_id'],
            "reply_to": self.amqp_message.properties['reply_to'],
            "replyToExchange": self.amqp_message.headers['replyToExchange']
        }
        # Send reply
        self.message_worker.publish(
            json.dumps(rsp_body, indent=4),
            resp_prop
        )
        return
