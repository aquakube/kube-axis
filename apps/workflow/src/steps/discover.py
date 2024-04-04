import logging
import logging

from utilities.axis import is_valid_axis_serial_number
from utilities.command import resolve_ip_address, resolve_mac_address
from utilities.state import save

logger = logging.getLogger(__name__)


def discover(resource: dict) -> str:
    """
    Discovers the AXIS cameras based on the provision strategy and returns its IP address.
    If the camera is not discovered, an exception is raised.
    If the camera does not have a valid serial number, an exception is raised.
    """
    ip_address = None
    mac_address = None

    # Resolve the AXIS camera via the provided MAC address
    if resource['spec']['workflow']['provision_strategy'] == 'resolve_mac_address':
        ip_address = resolve_ip_address(
            mac_address = resource['spec']['network']['mac_address'],
            subnet = resource['spec']['network']['subnet']
        )
        mac_address = resource['spec']['network']['mac_address']
    # Resolve the AXIS camera via the provided IP address
    elif resource['spec']['workflow']['provision_strategy'] == 'dhcp_ip_address':
        ip_address = resource['spec']['network']['dhcp_ip_address']
        mac_address = resolve_mac_address(
            ip_address = resource['spec']['network']['dhcp_ip_address'],
            subnet = resource['spec']['network']['subnet']
        )

    # Validate the mac address is a valid axis serial number
    if not is_valid_axis_serial_number(mac_address):
        raise Exception(f"MAC address: {mac_address} is not a valid Axis serial number")

    logger.info(f"Discovered AXIS camera at IP address '{ip_address}'")
    return ip_address


def run(resource: dict):
    """
    Attempts to discover the AXIS device given a MAC adress or IP address specified in the resource.
    If an AXIS camera is successfully discovered the state of the workflow is updated with the AXIS cameras IP address.
    If the AXIS camera cannot be discovered, an exception is raised and the workflow should exit to notify phase.
    """
    save(state={'ip_address': discover(resource)})
