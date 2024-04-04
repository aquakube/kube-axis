import os
import time
import logging
import platform
import subprocess
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

def ping(host: str):
    """
    Returns True or False with success of ping
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    return subprocess.call(command, stdout=open(os.devnull, 'wb')) == 0


def fast_ping(host):
    '''
    Floods the host with ping messages
    concurrently that will timeout quickly.
    Useful for quickly checking if device is up,
    routable, and network is in optimal state.

    Linux Docs: https://linux.die.net/man/8/ping
    -f => flood the pings. Cocurrent
    -n => numeric output only
    -W => Wait time in seconds for each ping
    -w => absolute timeout in seconds
    -c => how many pings to send

    returns:
        bool => true if status code of 0, false otherwise
        None => if exception occurs
    '''
    try:
        command = ['ping', '-n', '-f', '-W 3', '-w 5', '-c 5', host]
        status_code = subprocess.call(command, stdout=open(os.devnull, 'wb'))
        return status_code == 0
    except:
        logger.exception('Failed to execute fast ping')

    return None


def run_command(command: str, timeout=60) -> str:
    logger.info(f"Running shell command: {command}")

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate()
    stderr = stderr.decode("utf-8")
    stdout = stdout.decode("utf-8")
    exit_code = process.wait(timeout=timeout)

    logger.debug(f"Command exited with code: {exit_code}")
    logger.debug(f"Command stdout: {stdout}")

    if stderr:
        raise Exception(stderr)

    return stdout


def is_reachable(ip_address, timeout: int = 60) -> bool:
    """
    Attempts to reach out to the AXIS device at the provided ip_address via ICMP ping.
    If it fails after the provided timeout, provided in seconds, an exception will be thrown indicating the device is unreachable.
    """
    response = False
    start_time = time.time()

    while not response:
        response = ping(ip_address)

        if time.time() - start_time > timeout:
            raise Exception(f'AXIS Device at ip address: {ip_address} did not respond to pings')

    return True


def resolve_ip_address(mac_address: str, subnet: str) -> str:
    """
    This will return the ip address for the device if it is found on the network.
    If the device is not found, an exception will be thrown.

    Resolves the MAC address to an IP address using nmap. The subnet used
    will be scanned for all devices on the network. This function must be run
    as root and on the same direct layer 2 network as the device you are
    trying to resolve.
    """
    logger.info(f"Attempting to resolve MAC address '{mac_address}' to IP address")
    nmap_discover_command = f"sudo nmap --host-timeout 30 --max-retries 0 -sP -n -oX - {subnet}"
    output = run_command(nmap_discover_command)
    logger.debug(f"Nmap discover output: {output}")
    output = ET.fromstring(output)

    for host in output.findall('host'):
        addresses = [a for a in host.findall('address')]
        mac = [a for a in addresses if a.get('addrtype') == 'mac']
        ip = [a for a in addresses if a.get('addrtype') == 'ipv4']
        if mac and ip:
            mac = mac[0].get('addr').lower()
            ip = ip[0].get('addr').lower()

            if mac == mac_address:
                logger.info(f"Resolved MAC address '{mac_address}' to IP address '{ip}'")
                return ip
    else:
        raise Exception(f"Could not resolve MAC address: {mac_address} to IP address on subnet: {subnet}")


def resolve_mac_address(ip_address: str, subnet: str) -> str:
    """
    This will return the mac address for the device if it is found on the network.
    If the device is not found, an exception will be thrown.

    Resolves the IP address to an MAC address using nmap. The subnet used
    will be scanned for all devices on the network. This function must be run
    as root and on the same direct layer 2 network as the device you are
    trying to resolve.
    """
    logger.info(f"Attempting to resolve IP address '{ip_address}' to MAC address")
    nmap_discover_command = f"sudo nmap --host-timeout 30 --max-retries 0 -sP -n -oX - {subnet}"
    output = run_command(nmap_discover_command)
    logger.debug(f"Nmap discover output: {output}")
    output = ET.fromstring(output)

    for host in output.findall('host'):
        addresses = [a for a in host.findall('address')]
        mac = [a for a in addresses if a.get('addrtype') == 'mac']
        ip = [a for a in addresses if a.get('addrtype') == 'ipv4']
        if mac and ip:
            mac = mac[0].get('addr').lower()
            ip = ip[0].get('addr').lower()

            if ip == ip_address:
                logger.info(f"Resolved IP address '{ip_address}' to MAC address '{mac}'")
                return mac
    else:
        raise Exception(f"Could not resolve IP '{ip_address}' to mac address on subnet: {subnet}")
