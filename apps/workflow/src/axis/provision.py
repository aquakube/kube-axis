import json
import time
import logging

from utilities.vapix import VAPIX
from utilities.command import resolve_ip_address, is_reachable

logger = logging.getLogger(__name__)


def provision(resource: dict, state: dict) -> str:
    """
    Runs the provisioning process for setting up an AXIS camera network settings
    """
    # Initialize an instance of the camera API w/ the default root admin user credentials
    camera = VAPIX(
        name=resource['metadata']['name'],
        host=state['ip_address'],
        username='root',
        password='admin'
    )

    # update credentials for following steps
    state['username'] = camera.username
    state['password'] = camera.password

    logger.info(f"Attempting to provision AXIS camera {camera.name} - {camera.host}")

    # We need to create the initial root admin user to allow log-in access on the device.
    # The username must be root and the role must be Administrator with PTZ control. 
    # Please note that this user can only be created once and can not be deleted.
    if is_missing_initial_admin_user(camera):
        logger.info(f"AXIS camera {camera.name} is missing initial admin user. Creating...")
        create_axis_user(
            camera,
            username=camera.username,
            password=camera.password
        )

    # Verify that we have root access to the device
    if not has_root_access(camera):
        raise Exception(f"Cannot provision AXIS camera {camera.name} as the workflow could not achieve root access privileges")

    # Assign static ip address and hostname if network mode is 'static'
    if resource['spec']['network']['mode'] == 'static':
        # enable static IPv4 configuration
        assign_static_hostname(camera)
        assign_static_ipv4_address(
            camera,
            static_ip_address=resource['spec']['network']['static_ip_address'],
            router_ip_address=resource['spec']['network']['router_ip_address']
        )

        # if the ip address is changing, we need to wait for the camera to respond at the new ip address
        if state['ip_address'] != resource['spec']['network']['static_ip_address']:
            logger.info(f"Attempting to resolve the AXIS camera {camera.name} at the new static ip address '{resource['spec']['network']['static_ip_address']}'")
            is_reachable(
                ip_address=resource['spec']['network']['static_ip_address'],
                timeout=60
            )

        # Update state to reflect the new static ip address because the camera will now be
        # responding on this ip since it was just assigned.
        state['ip_address'] = resource['spec']['network']['static_ip_address']
        # Update the camera host to reflect the static ip address so future configure requests are successful
        camera.host = state['ip_address']

    # Enable DHCP address and hostname configuration if network mode is 'dhcp'
    elif resource['spec']['network']['mode'] == 'dhcp':
        # fetch initial network information
        data = get_network_info(camera)
        # Enable DHCP configuration
        enable_hostname_configuration_via_dchp(camera)
        enable_ipv4_address_configuration_via_dhcp(camera)

        # If the camera was not on dhcp initially, the assigend dhcp ip address may not immediately be available after enabling dhcp configuration
        mode = None
        for device in data['devices']:
            if device['name'] == 'eth0':
                mode = device['IPv4']['configurationMode']
                if mode != 'dhcp':
                    logger.info(f"Attemping to resolve the new DHCP assigned ip address for AXIS camera '{camera.name}'")
                    now = time.time()
                    while time.time() - now < 120:
                        resolved_ip_address = resolve_ip_address(
                            mac_address = resource['spec']['network']['mac_address'],
                            subnet = resource['spec']['network']['subnet']
                        )
                        # check if we can resolve the new dhcp ip address
                        # if resolved, update the state and break out of the loop
                        if resolved_ip_address != camera.host:
                            state['ip_address'] = resolved_ip_address
                            camera.host = state['ip_address']
                            break
                        else:
                            logger.info(f"Discovered the The DHCP assigned ip address for AXIS camera '{camera.name}' has not been assigned or responded yet. Will attempt to resolve the new dhcp address in 5 seconds...")
        else:
            # Update state to reflect the new DHCP ip address because the camera will now be
            # responding on this ip since it was just assigned.
            logger.info(f"AXIS camera '{camera.name}' was already on DHCP and should not have changed ip address. will attempt to resolve the camera again though.")
            state['ip_address'] = resolve_ip_address(
                mac_address = resource['spec']['network']['mac_address'],
                subnet = resource['spec']['network']['subnet']
            )
            if state['ip_address'] != camera.host:
                logger.warning(f"AXIS camera '{camera.name}' unexpectedly changed ip address from '{camera.host}' to '{state['ip_address']}'")
            # Update the camera host to reflect the dhcp ip address so future configure requests are successful
            camera.host = state['ip_address']

    logger.info(f"Successfully provisioned AXIS camera {camera.name} - {camera.host}")
    return state


def get_network_info(camera: VAPIX) -> dict:
    """
    Attempts to get the network info from the AXIS camera
    """
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "Forever Oceans Provisioning Process Fetching Network Info",
            "method": "getNetworkInfo"
        }
    )
    response = camera._network_settings(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when fetching network information..")

    result = response.json()
    error = result.get('error')
    if error:
        raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when getting network information. {error.get('message')}")
    else:
        logger.info(f"{camera.name} [{camera.host}] -  Successfully fetched network information")
        return result.get('data')



def is_missing_initial_admin_user(camera: VAPIX):
    """
    Returns True if camera is missing the initial root admin user. False otherwise.
    NOTE: if the camera is missing the initial root admin user,
    logging in to the device is impossible at this stage, no authentication is required to create it.
    """
    response = camera._user_management(params = {'action': 'get'})
    logger.debug(f'response: {response.status_code}, {response.text}')
    return bool(
        response is not None
        and response.status_code == 401
        and 'Error: initial admin user must be created first' in response.text
    )


def has_root_access(camera):
    """
    Returns True if the camera has root access. False otherwise.
    NOTE: authentication and admin privileges are required for all user handling operations.
    """
    response = camera._user_management(params = {'action': 'get'})
    logger.debug(f'response: {response.status_code}, {response.text}')
    return bool(
        response is not None
        and response.ok
    )


def create_axis_user(camera: VAPIX, username: str = 'root', password: str = 'admin') -> VAPIX:
    """
    Creates the specified user on the axis camera, this requires admin privileges.
    No authentication is required to create a user if the camera is missing the initial root admin user.
    """
    response = camera._user_management(
        params={
            'action': 'add',
            'user': username,
            'pwd': password,
            'sgrp': 'admin:operator:viewer:ptz',
            'grp': 'root'
        }
    )
    logger.info(f'response: {response.status_code}, {response.text}')
    if response and response.ok and 'Created' in response.text:
        logger.info(f"Successfully created axis user '{username}'")
    else:
        raise Exception(f"Failed to create axis user '{username}'")


def assign_static_ipv4_address(camera: VAPIX, static_ip_address: str, router_ip_address: str):
    """
    Set a static IPv4 address configuration so that device matches the official network layout for your farm

    Modifying the active IPv4 address configuration may disrupt the network connection between the device and the client,
    which is why this method will return once its input parameters have been validated,
    but before the network re-configuration is activated. In the event that the re-configuration fails,
    it is returned to its prior state and an error is written in the device's system log.
    """
    logger.info(f"Setting a static IPv4 address of {static_ip_address} to AXIS camera {camera.name}")
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "Assigning IP address configuration per aquakube Network Address Layout definitions",
            "method": "setIPv4AddressConfiguration",
            "params": {
                "deviceName": "eth0",
                "configurationMode": "static",
                "staticDefaultRouter": router_ip_address,
                "staticAddressConfigurations": [
                    {
                        "address": static_ip_address,
                        "prefixLength": 24,
                    }
                ]
            }
        }
    )
    response = camera._network_settings(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when assigning a static IP..")

    result = response.json()
    error = result.get('error')
    if error:
        raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when assigning static IPv4 address. {error.get('message')}")
    else:
        logger.info(f"{camera.name} [{camera.host}] -  Successfully assigned static IPv4 address of {static_ip_address}")


def assign_static_hostname(camera: VAPIX):
    """
    Set a static hostname configuration
    """
    logger.info(f"Setting a static host name of {camera.name} to AXIS camera")
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "Assigning hostname configuration per aquakube standards",
            "method": "setHostnameConfiguration",
            "params": {
                "staticHostname": camera.name
            }
        }
    )
    response = camera._network_settings(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when assigning static hostname '{camera.name}'..")

    result = response.json()
    error = result.get('error')
    if error:
        raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when assigning static hostname '{camera.name}'. {error.get('message')}")
    else:
        logger.info(f"{camera.name} [{camera.host}] -  Successfully assigned static hostname '{camera.name}'")


def enable_hostname_configuration_via_dchp(camera: VAPIX):
    """
    Enable an automatic hostname assignment on the device. Automatic IPv4 address assignment via DHCP must be enabled for this feature to work.
    """
    logger.info(f"Enabling an automatic hostname assignment on the AXIS camera  {camera.name}")
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "Assigning hostname configuration per aquakube standards",
            "method": "setHostnameConfiguration",
            "params": {
                "useDhcpHostname": True,
            }
        }
    )
    response = camera._network_settings(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when enabling hostname configuration via DHCP..")

    result = response.json()
    error = result.get('error')
    if error:
        raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when enabling automatic hostname assignment via DHCP. {error.get('message')}")
    else:
        logger.info(f"{camera.name} [{camera.host}] -  Successfully enabled automatic hostname assignment on device")


def enable_ipv4_address_configuration_via_dhcp(camera: VAPIX):
    """
    Enable IPv4 address configuration via DHCP
    """
    logger.info(f"Enabling an automatic IPv4 address assignment on the AXIS camera {camera.name} via DHCP")
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "Enabling IPv4 address configuration via DHCP",
            "method": "setIPv4AddressConfiguration",
            "params": {
                "deviceName": "eth0",
                "configurationMode": "dhcp"
            }
        }
    )
    response = camera._network_settings(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when enabling IPv4 address configuraiton via DHCP..")

    result = response.json()
    error = result.get('error')
    if error:
        raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when enabing DHCP address configuration. {error.get('message')}")
    else:
        logger.info(f"{camera.name} [{camera.host}] -  Successfully enabled IPv4 address configuration via DHCP")
