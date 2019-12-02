"""vCloud Director helpers functions.
"""
from vcdextproxy.utils import logger
from vcdextproxy.configuration import conf

from cachetools import cached, TTLCache

from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client
from pyvcloud.vcd.org import Org
from pyvcloud.vcd.role import Role


def login_from_token(token):
    """Return a client session to use with the user's token.

    Args:
        token (string): Auth token provided by user.

    Returns:
        pyvcloud.vcd.client.Client: Session to use with the user's token.
    """
    client = Client(
        conf('global.vcloud.hostname'),
        api_version=conf('global.vcloud.api_version'),
        verify_ssl_certs=conf('global.vcloud.ssl_verify', True),
        log_file=conf("global.pyvcloud.log_file"),
        log_requests=conf("global.pyvcloud.log_requests"),
        log_headers=conf("global.pyvcloud.log_headers"),
        log_bodies=conf("global.pyvcloud.log_bodies")
    )
    session = client.rehydrate_from_token(token)
    return client, session


def login_as_system_admin():
    """Create and returns a new session with the service account for the proxy.

    Returns:
        pyvcloud.vcd.client.Client: Session as service account.
    """
    client = Client(
        conf('global.vcloud.hostname'),
        api_version=conf('global.vcloud.api_version'),
        verify_ssl_certs=conf('global.vcloud.ssl_verify', True),
        log_file=conf("global.pyvcloud.log_file"),
        log_requests=conf("global.pyvcloud.log_requests"),
        log_headers=conf("global.pyvcloud.log_headers"),
        log_bodies=conf("global.pyvcloud.log_bodies")
    )
    credentials = BasicLoginCredentials(
        conf('global.vcloud.username'),
        conf('global.vcloud.system_org'),
        conf('global.vcloud.password')
    )
    client.set_credentials(credentials)
    logger.info(f"Connected to vCD as system administrator: {conf('global.vcloud.hostname')}")
    return client


@cached(TTLCache(maxsize=1000, ttl=conf("global.vcloud.cache_timeout")))
def list_rights_available_in_vcd(extension_name):
    """List the rights existing on this vCD instance.

    Args:
        extension_name (str): Name of the current extension
    """
    rights = []
    client = login_as_system_admin()
    system_org = Org(client, resource=client.get_org())
    return system_org.list_rights_available_in_vcd()


@cached(TTLCache(maxsize=1000, ttl=conf("global.vcloud.cache_timeout")))
def get_user_rights(user_client, user_session):
    """Lists rights of the current user.

    Args:
        client (pyvcloud.vcd.client.Client): Session of the requesting user

    Returns:
        list: List of rights IDs
    """
    user_rights_list = []
    # Start a sys admin session
    admin_client = login_as_system_admin()
    # Get org from user
    user_org = Org(user_client, resource=user_client.get_org())
    # Get admin object from the user's org
    admin_org = Org(admin_client, href=user_org.href)
    # Get role for user
    user_role = user_session.get('roles')
    # Get admin object from role
    admin_role = Role(
        admin_client,
        resource=user_org.get_role_resource(user_role))
    # Iterate on rights applied to the role
    for right in admin_role.list_rights():
        user_rights_list.append(right.get('id'))
    return user_rights_list