"""Fake vCloud Director client to run some tests.
"""
import json
import logging
import click
import requests

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

# pylint: disable=logging-fstring-interpolation


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

    def get(self, uri_path, parse_out=True):
        """Manage GET requests.

        Args:
            uri_path (str): path for the REST request.
            parse_out (bool): does the output need to be parse as json?

        Returns:
            content of the response body (as interpreted json if possible).
        """
        logger.info(f"New GET request to VCD API: {uri_path}")
        r = self.session.get(
            f"https://{self.hostname}{uri_path}",
            verify=self.verify_ssl
        )
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def post(self, uri_path, data, content_type="application/json", parse_out=True):
        """Manage POST requests.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (Optional:str): a content type for the request.
            parse_out (bool): does the output need to be parse as json?

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
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content


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


@click.command()
@click.option('-h', '--host', help="vCD server to use")
@click.option('-u', '--username', help="Username for vCD")
@click.option('-p', '--password', help='Password for vCD user')
@click.option('-k', '--no_verify', is_flag=False, help="Ignore SSL errors")
def main(host, username, password, no_verify):
    """Execute the client.
    """
    vcd_sess = VcdSession(host, username password,
        api_version="31.0", verify_ssl=not no_verify)
    logger.info("List current orgs for the user")
    for org in vcd_sess.get('/api/org').get("org", []):
        print(org)


if __name__ == '__main__':
    main()