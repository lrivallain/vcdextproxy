"""vCloud Director helpers functions.
"""
import json
import requests
from vcdextproxy.utils import logger
from vcdextproxy.configuration import conf
from cachetools import cached, TTLCache


class VcdSession():
    """Manage a vCD Session to proceed API requests with an auth context.
    """

    def __init__(self,
                 hostname: str,
                 username: str = None,
                 password: str = None,
                 token: str = None,
                 api_version: str = "33.0",
                 ssl_verify: bool = True,
                 logger_prefix: str = ""):
        """Create a new connector to a vCD.

        Args:
            hostname (str): vCloud Hostname
            username (str, optional): Username for the login process. Defaults to None.
            password (str, optional): Password of the user. Defaults to None.
            token (str, optional): An existing auth session token. Defaults to None.
            api_version (str, optional): API version to use (depends on your vCD version). Defaults to "33.0".
            verify_ssl (bool, optional): Check SSL certificates? Defaults to True.
            logger_prefix (str, optionnal): A prefix for logging purpose
        """
        self.logger_prefix = logger_prefix
        if not (username and password) and not token:
            self.log('error', "At least one of username+password or token is mandatory to initiate a new session.")
            return None
        self.hostname = hostname
        self.api_version = api_version
        self.ssl_verify = ssl_verify
        self.session = requests.session()
        self.session.headers.update(
            {'Accept': f"application/*+json;version={api_version}"})
        if not token:
            self.log('info', f"Starting a fresh session for on username {username}")
            token = self.generate_auth_token(username, password)
        else:
            self.log('info', "Reusing an exisiting session with provided token")
        self.update_headers(token)

    def log(self, level, message, *args, **kwargs):
        """Log a information about this object by adding a prefix

        Args:
            level (str): Log level for the information
            message (str): Message to log
        """
        _message = f"[{self.logger_prefix}] {str(message)}"
        try:
            getattr(logger, level)(_message)  # , args, kwargs)
        except AttributeError:
            self.log("error", f"Invalid log level {level} used: please fix in code.")
            self.log("debug", message, *args, **kwargs)  # loop with a sure status

    def update_headers(self, token: str):
        """Update headers for the current vCD session context.

        Args:
            token (str): Auth token used in the session.
        """
        if "Bearer" in token:
            self.log('debug', f"Use Bearer token auth method")
            self.session.headers.update({
                'Authorization': token,
            })
        else:
            self.log('debug', f"Use x-vcloud-authorization token auth method")
            self.session.headers.update({
                'x-vcloud-authorization': token,
            })

    def get(self, uri_path: str, parse_out: bool = True, full_return: bool = False):
        """Manage GET requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            parse_out (bool, optional): does the output need to be parsed as json? Defaults to True.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
            full_return (bool, optionnal): return the full response object? Default to False.
        """
        self.log('info', f"New request to vCD: {uri_path}")
        r = self.session.get(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify
        )
        if int(r.status_code) >= 300:
            self.log('error', f"Invalid response code received {r.status_code} with content: {r.content}")
            if full_return:
                return r
            if parse_out:
                return {}  # Empty answer
            else:
                return ""  # Empty answer
        if full_return:
            return r
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def post(self, uri_path: str, data: str, content_type: str = "application/json",
             parse_out: bool = True, full_return: bool = False):
        """Manage POST requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (str, optionnal): a content-type for the request. Defaults to "application/json"
            parse_out (bool, optionnal): does the output need to be parse as json? Defaults to True.
            full_return (bool, optionnal): return the full response object? Default to False.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
        """
        self.log('info', f"New POST request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        if content_type == "application/json":
            data = json.dumps(data)
        r = self.session.post(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify,
            data=data
        )
        if int(r.status_code) >= 300:
            self.log('error', f"Invalid response code received {r.status_code} with content: {r.content}")
            if full_return:
                return r
            if parse_out:
                return {}  # Empty answer
            else:
                return ""  # Empty answer
        if full_return:
            return r
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def put(self, uri_path: str, data: str, content_type: str = "application/json",
            parse_out: bool = True, full_return: bool = False):
        """Manage PUT requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (str, optionnal): a content-type for the request. Defaults to "application/json"
            parse_out (bool, optionnal): does the output need to be parse as json? Defaults to True.
            full_return (bool, optionnal): return the full response object? Default to False.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
        """
        self.log('info', f"New PUT request to VCD API: {uri_path}")
        self.session.headers["Content-Type"] = content_type
        if content_type == "application/json":
            data = json.dumps(data)
        r = self.session.put(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify,
            data=data
        )
        if int(r.status_code) >= 300:
            self.log('error', f"Invalid response code received {r.status_code} with content: {r.content}")
            if full_return:
                return r
            if parse_out:
                return {}  # Empty answer
            else:
                return ""  # Empty answer
        if full_return:
            return r
        if parse_out:
            return json.loads(r.content)
        else:
            return r.content

    def delete(self, uri_path: str, parse_out: bool = True, full_return: bool = False):
        """Manage DELETE requests within a vCD Session context.

        Args:
            uri_path (str): path for the REST request.
            data (str): data to set as request body.
            content_type (str, optionnal): a content-type for the request. Defaults to "application/json"
            parse_out (bool, optionnal): does the output need to be parse as json? Defaults to True.
            full_return (bool, optionnal): return the full response object? Default to False.

        Returns:
            dict or str: Content of the response body (as interpreted json if possible).
        """
        self.log('info', f"New DELETE request to VCD API: {uri_path}")
        r = self.session.delete(
            f"https://{self.hostname}{uri_path}",
            verify=self.ssl_verify,
        )
        if int(r.status_code) >= 300:
            self.log('error', f"Invalid response code received {r.status_code} with content: {r.content}")
            if full_return:
                return r
            if parse_out:
                return {}  # Empty answer
            else:
                return ""  # Empty answer
        if full_return:
            return r
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
        r = self.post(
            f"/api/sessions",
            data=None,
            full_return=True
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
        self.log('trivia', f"Organizations for the current user: " + json.dumps(orgs, indent=2))
        return orgs

    def is_org_member(self, org_id: str):
        """Return the membership of a user to an organization.

        Args:
            org_id (str): Organization id to test the current user membership.

        Returns:
            bool: Is the current user a member of the organization ?
        """
        self.log('debug', f"Checking is current user is member of the org with id {org_id}")
        membership = any(org['id'] == org_id for org in self.list_organizations_membership())
        if not membership:
            self.log('warning', f"Current user is not a member of org with id {org_id}")
        else:
            self.log('debug', f"Current user is a member of org with id {org_id}")
        return membership

    def has_right(self, user_rights: str, ref_right_id: str):
        """Does the user of the current session have the reference right ?

        Args:
            user_rights (list): List of the user rights
            ref_right_id (str): Reference right id
        """
        for right in user_rights:
            if ref_right_id in right:
                self.log('debug', f"Current user has the reference right.")
                return True
        self.log('warning', f"Current user does not have the reference right.")
        return False

    def query(self, type: str, format: str = "records", filter: str = "", page: int = 1):
        """Exceute a typed query on vCD session

        Args:
            type (str): Type of object to retrieve
            format (str, optional): Return format. Defaults to "records".
            filter (str, optional): Filter for the query. Defaults to "".
        """
        uri = f"/api/query?type={type}&format={format}"
        uri += f"&page={page}&filterEncoded=true&filter={filter}"
        data = self.get(uri)
        if format == "records":
            return data.get("record")
        else:
            return data


@cached(TTLCache(maxsize=1000, ttl=conf("global.vcloud.cache_timeout")))
def get_vcd_rights(extension_name):
    """List the rights existing on this vCD instance.

    Args:
        extension_name (str): Name of the current extension
    """
    vcd_sess = VcdSession(
        hostname=conf('global.vcloud.hostname'),
        username=conf('global.vcloud.username'),
        password=conf('global.vcloud.password'),
        api_version=conf('global.vcloud.api_version'),
        ssl_verify=conf('global.vcloud.ssl_verify', True),
        logger_prefix=extension_name
    )
    rights = []
    for org in vcd_sess.list_organizations_membership():
        if org['name'].lower() == 'system':
            rights_path = f"/api/admin/org/{org['id']}/rights"
            for right in vcd_sess.get(rights_path).get("rightReference", []):
                rights.append({
                    'id': right['href'].split('/')[-1],
                    'name': right['name']
                })
            return rights
    logger.error("[{extension_name}] Only members of the System organization can list the existings rights.")
    return rights
