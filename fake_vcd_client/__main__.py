"""Fake vCloud Director client to run some tests.
"""
import json
import logging
import click
import requests
import time

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class VcdSession():
    """Manage a vCD Session to proceed API requests with an auth context.
    """

    def __init__(self, hostname, username, password,
        api_version="31.0", verify_ssl=True):

        """Create a new connector to a vCD.
        """
        self.hostname = hostname
        self.api_version = api_version
        self.verify_ssl = verify_ssl
        self.session = requests.session()
        self.session.headers.update({
            'Accept': f"application/*+json;version={api_version}"
        })
        logger.info(f"Starting a fresh session for on username {username}")
        self.session.headers.update({
            'x-vcloud-authorization': self.get_auth_token(username, password),
        })

    def get(self, uri_path):
        """Manage GET requests.

        Args:
            uri_path (str): path for the REST request.

        Returns:
            content of the response body (as interpreted json if possible).
        """
        logger.info(f"New GET request to VCD API: {uri_path}")
        r = self.session.get(
            f"https://{self.hostname}{uri_path}",
            verify=self.verify_ssl
        )
        return r

    def post(self, uri_path, data, content_type="application/json"):
        """Manage POST requests.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (Optional:str): a content type for the request.

        Returns:
            dict or str: content of the response body (as interpreted json if possible).
        """
        logger.info(f"New POST request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        if content_type == "application/json":
            data = json.dumps(data)
        r = self.session.post(
            f"https://{self.hostname}{uri_path}",
            verify=self.verify_ssl,
            data=data
        )
        return r

    def put(self, uri_path, data, content_type="application/json"):
        """Manage PUT requests.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (Optional:str): a content type for the request.

        Returns:
            dict or str: content of the response body (as interpreted json if possible).
        """
        logger.info(f"New PUT request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        if content_type == "application/json":
            data = json.dumps(data)
        r = self.session.put(
            f"https://{self.hostname}{uri_path}",
            verify=self.verify_ssl,
            data=data
        )
        return r

    def delete(self, uri_path, content_type="application/json"):
        """Manage DELETE requests.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (Optional:str): a content type for the request.

        Returns:
            dict or str: content of the response body (as interpreted json if possible).
        """
        logger.info(f"New DELETE request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        r = self.session.delete(
            f"https://{self.hostname}{uri_path}",
            verify=self.verify_ssl
        )
        return r

    def get_auth_token(self, username, password):
        """Retrieve an auth token to authenticate user for further requests.

        Args:
            username (str): Username.
            password (str): User's password.

        Returns:
            str: A x-vcloud-authorization token.
        """
        self.session.auth = (username, password)
        r = self.session.post(
            f"https://{self.hostname}/api/sessions",
            verify=self.verify_ssl,
            data=None
        )
        return r.headers.get('x-vcloud-authorization', None)


def print_r(r):
    data = [
        r.request.method,
        r.request.url,
        str(r.status_code),
        r.content[:40]
    ]
    print(" - ".join(data))

@click.command()
@click.option('-h', '--host', help="vCD server to use", required=True)
@click.option('-u', '--username', help="Username for vCD", required=True)
@click.option('-p', '--password', help='Password for vCD user', required=True)
@click.option('-k', '--no_verify', is_flag=True, help="Ignore SSL errors")
@click.option('-s', '--sleep', default=1, help="Sleep time between requests")
def main(host, username, password, no_verify, sleep):
    """Execute the client.
    """
    hello_world = {"hello": "world"}
    vcd_sess = VcdSession(host, username, password,
        api_version="31.0", verify_ssl=not no_verify)
    logger.info("List current orgs for the user")
    for org in json.loads(vcd_sess.get('/api/org').content).get("org", []):
        print(json.dumps(org, indent=2))
    while True:
        logger.info("Requesting data from example1")
        print_r(vcd_sess.get('/api/example1/test/toto'))
        time.sleep(sleep)
        logger.info("Requesting data from example2")
        print_r(vcd_sess.get('/api/this/is/1/test/example2/test/azerty?toto'))
        time.sleep(sleep)
        logger.info("Posting data to example1")
        print_r(vcd_sess.post('/api/example1/test/toto', hello_world))
        time.sleep(sleep)
        logger.info("Deleting data in example1")
        print_r(vcd_sess.delete('/api/example1/test/toto'))
        time.sleep(sleep)
        logger.info("Updating data in example2")
        print_r(vcd_sess.put('/api/this/is/1/test/example2/test/azerty', hello_world))
        time.sleep(sleep)


if __name__ == '__main__':
    main()
