"""vCloud Director helpers functions.
"""
import json
import requests
from vcdextproxy.utils import logger
from vcdextproxy.configuration import conf

class VcdSession():
    """Manage a vCD Session to proceed API requests with an auth context.
    """

    def __init__(
            self,
            hostname: str,
            username: str=None,
            password: str=None,
            token: str=None,
            api_version: str="33.0",
            ssl_verify: bool=True
        ):
        """Create a new connector to a vCD.

        Args:
            hostname (str): vCloud Hostname
            username (str, optional): Username for the login process. Defaults to None.
            password (str, optional): Password of the user. Defaults to None.
            token (str, optional): An existing auth session token. Defaults to None.
            api_version (str, optional): API version to use (depends on your vCD version). Defaults to "33.0".
            verify_ssl (bool, optional): Check SSL certificates? Defaults to True.
        """
        if not (username and password) and not token:
            logger.error("At least one of username+password or token is mandatory to initiate a new session.")
            return None
        self.hostname = hostname
        self.api_version = api_version
        self.ssl_verify = ssl_verify
        self.session = requests.session()
        if not token:
            logger.info(f"Starting a fresh session for on username {username}")
            token = self.generate_auth_token(username, password)
        else:
            logger.info("Reusing an exisiting session with provided token")
        self.update_headers(token, api_version)

    def update_headers(self, token: str, api_version):
        """Update headers for the current vCD session context.

        Args:
            token (str): Auth token used in the session.
        """
        if "Bearer" in token:
            logger.debug(f"Use Bearer token auth method")
            self.session.headers.update({
                'Authorization': token,
            })
        else:
            logger.debug(f"Use x-vcloud-authorization token auth method")
            self.session.headers.update({
                'x-vcloud-authorization': token,
            })
        self.session.headers.update(
            {'Accept': f"application/*+json;version={api_version}"})

    def get(self, uri_path: str, parse_out: bool=True):
        """Manage GET requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            parse_out (bool, optional): does the output need to be parsed as json? Defaults to True.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
        """
        logger.info(f"New request to vCD: {uri_path}")
        r = self.session.get(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify
        )
        if int(r.status_code) >= 300:
            logger.error(f"Invalid response code received {r.status_code} with content: {r.content}")
            if parse_out:
                return {} # Empty answer
            else:
                return ""  # Empty answer
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def post(self, uri_path: str, data: str, content_type: str="application/json", parse_out: bool=True):
        """Manage POST requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (str, optionnal): a content-type for the request. Defaults to "application/json"
            parse_out (bool, optionnal): does the output need to be parse as json? Defaults to True.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
        """
        logger.info(f"New POST request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        if content_type == "application/json":
            data = json.dumps(data)
        r = self.session.post(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify,
            data=data
        )
        if int(r.status_code) >= 300:
            logger.error(f"Invalid response code received {r.status_code} with content: {r.content}")
            if parse_out:
                return {} # Empty answer
            else:
                return ""  # Empty answer
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def generate_auth_token(self, username: str, password: str):
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
            verify=self.ssl_verify,
            data=None
        )
        return r.headers.get('x-vcloud-authorization', None)

    def list_organizations_membership(self):
        """Get the organization(s) where the current user belongs to.

        Returns:
            list: A list of the organization(s) as id/name dict.
        """
        orgs = []
        for org in self.get('/api/org').get("org", []):
            valid_org = {
                'id': org['href'].split('/')[-1],
                'name': org['name'].lower()
            }
            orgs.append(valid_org)
        logger.trivia(f"Organizations for the current user: " + json.dumps(orgs, indent=2))
        return orgs

    def is_org_member(self, org_id: str):
        """Return the membership of a user to an organization.

        Args:
            org_id (str): Organization id to test the current user membership.

        Returns:
            bool: Is the current user a member of the organization ?
        """
        logger.debug(f"Checking is current user is member of the org with id {org_id}")
        membership = any(org['id'] == org_id for org in self.list_organizations_membership())
        if not membership:
            logger.warning(f"Current user is not a member of org with id {org_id}")
        else:
            logger.debug(f"Current user is a member of org with id {org_id}")
        return membership