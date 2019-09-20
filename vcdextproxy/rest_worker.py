#!/usr/bin/env python
"""The REST worker is in charge of dealing with REST API backends.
"""

import base64
import json
import requests
import json
from threading import Thread
from requests.auth import HTTPBasicAuth
from vcdextproxy.configuration import conf


class RESTWorker(Thread):
    def __init__(self, extension, message_worker, data, message):
        Thread.__init__(self)
        self.extension = extension
        # enable to publish response from the worker
        self.message_worker = message_worker
        # split request content from vcd context data
        self.req_data = data[0]
        self.vcd_data = data[1]
        # message metadata
        self.amqp_message = message
        # get message ID
        self.id = self.req_data['id']
        # get the current auth token
        self.token = None
        for header_key, header_value in self.headers.items():
            if header_key.lower() == "x-vcloud-authorization" or header_key.lower() == "authorization" :
                self.token = header_value

    def forge_headers(self):
        """Returns all the headers for requests to backend

        Returns:
            dict: The headers dictionnary
        """
        headers = dict(self.req_data.get('headers', {}))
        # parse information from vcd request metadata. Add them to request headers #10
        headers['org_id'] = self.vcd_data.get('org', '').split("urn:vcloud:org:")[1]
        headers['user_id'] = self.vcd_data.get('user', '').split("urn:vcloud:user:")[1]
        self.extension.log('trivia', "Headers (without rights): " + json.dumps(headers, indent=2))
        headers['user_rights'] = json.dumps(self.vcd_data.get('rights'))
        return headers

    def pre_checks(self):
        """Run some pre-checks like checking rights.
        """
        #TODO: check rights + org membership
        return True

    def reply(self, rsp_body, status_code):
        """Send reply to the request

        Args:
            rsp_body (str): body of the answer as string
            status_code (int): HTTP response code
        """
        # prepare reply properties
        self.extension.log('info', f"Replying with HTTP response code: {status_code}")
        # if body is a dict, then stringify it
        if isinstance(rsp_body, dict):
            rsp_body = json.dumps(rsp_body)
        resp_prop = {
            "routing_key": self.amqp_message.delivery_info['routing_key'], # for mapping in amqp/publisher
            "id": self.id,
            "accept": self.headers.get('Accept', None),
            "correlation_id": self.amqp_message.properties['correlation_id'],
            "reply_to": self.amqp_message.properties['reply_to'],
            "replyToExchange": self.amqp_message.headers['replyToExchange'],
            "statusCode": status_code
        }
        # Send reply
        self.message_worker.publish(rsp_body, resp_prop)

    def run(self):
        """Handle all messages received on the RabbitMQ Exchange.
        """
        # decode request body
        body = base64.b64decode(self.req_data.get('body', ''))
        # search the current auth token in headers
        if not self.pre_checks():
            raise Exception("Pre check error") #TODO: Do better exceptions
        # search the appropriate requests attr
        try:
            # Get the requests function based on the requested method
            forward_request = getattr(
                requests,
                self.req_data.get('method', 'get').lower()
            )
        except AttributeError as e:
            self.extension.log('error', f"The method {method} is not supported.")
            rsp_body = {"Error": f"The method {method} is not supported."}
            status_code = 405
            self.reply(rsp_body, status_code)
        except Exception as e:
            self.extension.log('error', f"Unmanaged error raised: {str(e)}")
            raise e # raise other errors as usual
        # forward the requests to the backend
        try:
            r = forward_request(
                self.extension.get_full_url(
                    full_req_path += self.req_data.get('requestUri', "")
                    query_string = self.req_data.get('queryString')
                ),
                data=body,
                auth=self.extension.get_extension_auth(),
                headers=self.forge_headers()
                verify=self.extension.get_conf('backend.verify', True),
                timeout=self.extension.get_conf('backend.timeout', 300) # by default 5 minutes timeout
            )
            rsp_body = r.text
            status_code = r.status_code
        except requests.exceptions.Timeout:
            self.extension.log('warning', "Timeout from extension backend server")
            rsp_body = {"Error": "Timeout from extension backend server"}
            status_code = 504
        except requests.exceptions.TooManyRedirects:
            self.extension.log('warning', "TooManyRedirects from extension backend server")
            rsp_body = {"Error": "TooManyRedirects from extension backend server"}
            status_code = 508
        except requests.exceptions.ConnectionError as e:
            self.extension.log('warning', "ConnectionError from the extension backend server")
            rsp_body = {"Error": "ConnectionError from the extension backend server"}
            status_code = 503
        except requests.exceptions.RequestException as e:
            self.extension.log('warning', "RequestException from extension backend server")
            rsp_body = {"Error": "RequestException from extension backend server"}
            status_code = 502
        except Exception as e:
            self.extension.log('error', f"Unmanaged error raised: {str(e)}", exc_info=1)
            rsp_body = {"Error": "Unmanaged error raised"}
            status_code = 500
        self.reply(rsp_body, status_code)
        return
