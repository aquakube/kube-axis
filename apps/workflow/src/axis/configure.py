import os
import time
import json
import logging
from xml.etree import ElementTree

import boto3

from utilities.vapix import VAPIX
from utilities.command import ping

logger = logging.getLogger()

# Constants
# These may be exposed as configuration options in the future
DEFAULT_FILESYSTEM_FORMAT = 'ext4'
DEFAULT_TEXT_OVERLAY = "%D %X"
PRODUCTION_AXIS_FIRMWARE_FILENAME = 'M3058-PLVE_10_12_166.bin'
S3_FIRMWARE_BUCKET = 'aquakube-axis-firmware'
PRODUCTION_FIRMWARE_RELEASE = '10.12.166'


def configure(resource: dict, state: dict):
    """
    Configures the axis device
    """
    camera = camera = VAPIX(
        name=resource['metadata']['name'],
        host=state['ip_address'],
        username=state['username'],
        password=state['password'] 
    )

    max_retries = resource['spec']['workflow']['max_retries']
    retry_delay = resource['spec']['workflow']['retry_delay']
    for _ in range(max_retries):
        try:
            allow_anonymous_viewers(camera)
            configure_camera_orientation(camera, orientation=resource['spec']['video']['orientation'])
            configure_recordings_retention_policy(camera, days=365)
            enable_snmp(camera)

            if resource['spec']['workflow']['ignore_firmware_version'] is False:
                check_firmware(camera)

            configure_ntp_client(camera)
            disk_check(camera)
            set_zipstream_gop_settings(camera)
            set_zipstream_strength(camera, strength=resource['spec']['video']['zipstream_strength'])
            configure_textoverlays(camera)
        except Exception as e:
            logger.exception(f"{camera.name} Failed configuration on attempt { ( _ + 1 )} of {max_retries}")
            # if max retries are met raise an exception with the traceback so the workflow will fail and the user can be notified of the issue
            if (_ + 1) == max_retries:
                raise e
            time.sleep(retry_delay)
        else:
            logger.info(f"{camera.name} Successfully configured on attempt { ( _ + 1 )} of {max_retries}")
            break


def allow_anonymous_viewers(camera: VAPIX):
    """ 
    Must allow anonymous viewers so live streams can be viewed on C2 UI.
    """
    response = camera._parameter_management(method='GET', params={'action': 'update', 'System.BoaProtViewer': 'anonymous', 'Network.RTSP.ProtViewer': 'anonymous'})

    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to allow anonymous viewers, stream will not be accessable on C2 UI..")
    
    logger.debug(f"{camera.name} [{camera.host}] Allow anonymous RTSP viewers response: {response.text}")
    logger.info(f"{camera.name} [{camera.host}] -  Allowing anonymous viewers")


def configure_camera_orientation(camera: VAPIX, orientation: str):
    """
    The camera orientation setting affects how view modes and the pan/tilt/zoom functionality are working.
    Wall mounting eliminates views modes [3] Double Panorama, [4] Quad View, [9] Corner Left, [10] Corner Right, [11] Double Corner

    ImageSource.I0.CameraTiltOrientation:
        -90 = Select this option if the camera is mounted in the ceiling.
        0 = Select this option if the camera is mounted on a wall.
        90 = Select this option if the camera is mounted on a desk or similar.
    """
    mapping = {'-90': 'ceiling', '0': 'wall', '90': 'desk'}
    response = camera._parameter_management(method='GET', params={'action': 'list', 'group': 'ImageSource.I0.CameraTiltOrientation'})

    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed get camera orientation.")
    
    logger.debug(f"{camera.name} [{camera.host}] List camera orientation response: {response.text}")
    _orientation = mapping.get(response.text.strip().split('=')[-1])
    logger.info(f"{camera.name} [{camera.host}] -  Camera orientation configured as {_orientation} mount")
    if _orientation != orientation:
        set_camera_orientation(camera, orientation)



def set_camera_orientation(camera: VAPIX, orientation: str):
    """
    Orientation is specified in devices.py,
    Users are prompted to update orientation to ensure the settings are correct
    """
    logger.info(f"{camera.name} [{camera.host}] -  Updating oritentation to '{orientation}' mount")
    response = camera._parameter_management(
        method='GET',
        params={
            'action': 'update',
            'group': 'ImageSource.I0.CameraTiltOrientation',
            'ImageSource.I0.CameraTiltOrientation': orientation,
        },
    )

    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to update camera orientation to {orientation}.")

    logger.debug(f"{camera.name} [{camera.host}] Set camera orientation response: {response.text}")
    logger.info(f"{camera.name} [{camera.host}] -  Successfully updated orientation as {orientation} mount")


def configure_recordings_retention_policy(camera: VAPIX, days=365):
    """ 
    During provisioning process we need to extend the retention policy from the default 7 days max age.

    Note: Recordings will be deleted earlier if the disk becomes full. Clean up policy is set to fifo.
    """
    response = camera._parameter_management(method='GET', params={'action': 'update', 'Storage.S0.CleanupMaxAge': days})

    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to extend retention polict to {days} days..")

    logger.debug(f"{camera.name} [{camera.host}] Extending retention policy (clean up max age = {days} days)  response: {response.text}")
    logger.info(f"{camera.name} [{camera.host}] -  Extended retention policy to {days} days")


def enable_snmp(camera: VAPIX):
    """ Enables SNMP so the device can be monitored from zabbix """
    response = camera._parameter_management(method='GET', params={'action': 'update', 'SNMP.Enabled': 'yes', 'SNMP.V1': 'yes', 'SNMP.V2c': 'yes', 'SNMP.V3': 'no', 'SNMP.V1ReadCommunity': 'public'})

    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to enable SNMP")

    logger.debug(f"{camera.name} [{camera.host}] Enabling SNMP  response: {response.text}")
    logger.info(f"{camera.name} [{camera.host}] -  Enabled SNMP")


def check_firmware(camera: VAPIX):
    """
    Axis cameras should all run the same produciton firmware release version.
    If firmware is out of date then firmware will be upgraded and perform a system reboot.
    """
    response = camera._firmware_management(method='GET', params={'apiVersion': '1.0', 'context': 'FO Configuration Management', 'method': 'status'})
    if response.ok:
        result = response.json()
        logger.debug(f"{camera.name} [{camera.host}] Check firmware response: {response.text}")
        active_firmware_version = result.get('data', {}).get('activeFirmwareVersion')
        if active_firmware_version != PRODUCTION_FIRMWARE_RELEASE:
            print(
                f"{camera.name} [{camera.host}] -  Firmware version {active_firmware_version} is out of date with production release version {PRODUCTION_FIRMWARE_RELEASE}"
            )
            logger.info(f"{camera.name} [{camera.host}] -  Updating firmware from {active_firmware_version} to {PRODUCTION_FIRMWARE_RELEASE}. This could take a couple minutes..")
            upgrade_firmware(camera)
        else:
            logger.info(f"{camera.name} [{camera.host}] -  Firmware is up to date on version {active_firmware_version}")
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Something went wrong with firmware check..")


def download_file_from_s3(s3_bucket: str, filename: str) -> str:
    """ Downloads the file from an s3 bucket if it does not already exist """
    cwd = os.getcwd()
    firmware = f'{cwd}/{filename}'
    if not os.path.isfile(firmware):
        s3 = boto3.client('s3')
        s3.download_file(s3_bucket, filename, firmware)
    return firmware


def upgrade_firmware(camera: VAPIX):
    """
    Upgrades the firmware to production release. 
    After an upgrade the device will be rebooted and the method waits for the device to come back online before returning.
    Security level: admin
    """
    firmware = download_file_from_s3(s3_bucket=S3_FIRMWARE_BUCKET, filename=PRODUCTION_AXIS_FIRMWARE_FILENAME)
    payload = open(firmware, 'rb')
    response = camera._upgrade_firmware(data=payload)
    if response and response.ok:
        logger.info(response.text)
        if 'Error' in response.text:
            raise Exception(f"{camera.name} [{camera.host}] -  Error when updating firmware. {response.text}")
        logger.info(f"{camera.name} [{camera.host}] -  Successfully upgraded firmware to {PRODUCTION_FIRMWARE_RELEASE}")
        logger.info(
            f"{camera.name} [{camera.host}] -  Waiting for device to come back online after reboot on successfull upgrade to {PRODUCTION_FIRMWARE_RELEASE}"
        )
        wait_on_reboot(host=camera.host, threshold=10)
        check_firmware(camera)
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Something went wrong with firmware upgrade..")


def wait_on_reboot(host: str, threshold=20):
    """ Returns when successful ping count is greater then threshold """
    count = 0
    while count <= threshold:
        online = ping(host)
        count += 1 if online else 0
        time.sleep(1)


def configure_ntp_client(camera: VAPIX):
    """
    Configures the axis cam to synchronize its internal clock and date by using NTP.
    If NTP is not configured properly then RTSP timeouts will occur and live streams can become unreliable.
    """
    payload = json.dumps(
        {
            'apiVersion': '1.0',
            'context': 'FO Configuration Management',
            'method': 'setNTPClientConfiguration',
            'params': {'enabled': True, 'serversSource': 'static', 'staticServers': ['time.nist.gov']},
        }
    )
    response = camera._ntp_client(data=payload)
    if not response or not response.ok:
        raise Exception(f"{camera.name} [{camera.host}] - Something went wrong when configuring NTP client..this could cause RTSP timeouts on live streams")
    try:
        logger.debug(f"{camera.name} [{camera.host}] Configure NTP Client response: {response.text}")
        result = response.json()
        error = result.get('error')
        if error:
            raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when configuring NTP client. {error.get('message')}")
        else:
            logger.info(f"{camera.name} [{camera.host}] -  Successfully configured NTP client")
    except json.decoder.JSONDecodeError:
        raise Exception(f"{camera.name} [{camera.host}] Failed to decode VAPIX NTP client configuration response, possible malformed response from axis client..")


def disk_check(camera: VAPIX):
    """
    Performs a check for SD card and reports back what it found.
    If the SD card was not formatted with ext4, prompt the user if the disk should be formatted.
    The SD cards are not preformatted, and need to be formatted before storage is enabled.

    SD cards can be formatted with ext4 or vfat. 
    Using ext4 is recommended to reduce the risk of data loss if the card is ejected and after abrupt power cycling
    """
    response = camera._list_disks(params={'diskid': 'all'})

    if not response or not response.ok:
        raise Exception(f'{camera.name} [{camera.host}] -  Something went wrong... Failed to list disks')

    logger.debug(f"{camera.name} [{camera.host}] Disk check response: {response.text}")
    root = ElementTree.fromstring(response.content)
    disk = root.find('disks').find('disk')

    status = disk.get('status')
    total_size = round(int(disk.get('totalsize')) / 1e6)  # convert kB to GB
    free_size = round(int(disk.get('freesize')) / 1e6)  # convert kB to GB
    filesystem = disk.get('filesystem')

    logger.info(f'{camera.name} [{camera.host}] -  SD card status: {status}, total size: {total_size}GB, free size: {free_size}GB, filesystem: {filesystem}')
    if filesystem != DEFAULT_FILESYSTEM_FORMAT and status != 'disconnected':
        logger.info(f"Reformat SD card to {DEFAULT_FILESYSTEM_FORMAT} filesystem")
        logger.warning("IMPORTANT: Any data present on the disk is lost when the disk is formatted.")
        format_disk(camera, disk_id=disk.get('diskid'))


def mount_disk(camera: VAPIX, action, disk_id):
    """ Mount/Unmount when formatting SD Card """
    response = camera._disk_mount(params={'action': action, 'diskid': disk_id})
    if not response:
        raise Exception(f"{camera.name} [{camera.host}] - Error on request to {action} disk")
    logger.debug(f"{camera.name} [{camera.host}] Disk mount response: {response.text}")
    root = ElementTree.fromstring(response.content)
    job = root.find('job')
    result = job.get('result') if isinstance(job, ElementTree.Element) else None
    if result == 'OK':
        logger.info(f"{camera.name} [{camera.host}] -  Successfully {action}ed disk")
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to {action} disk")


def format_disk(camera: VAPIX, disk_id):
    """ Formats the SD card to the default fileystem format specified """
    response = camera._format_disk(params={'diskid': disk_id, 'filesystem': DEFAULT_FILESYSTEM_FORMAT})
    if response and response.status_code == 403:
        # Need to unmount disk if this error is thrown and try again.
        mount_disk(camera, action='unmount', disk_id=disk_id)
        response = camera._format_disk(params={'diskid': disk_id, 'filesystem': DEFAULT_FILESYSTEM_FORMAT})

    if not response:
        raise Exception(f"{camera.name} [{camera.host}] -  Error on request to format disk to {DEFAULT_FILESYSTEM_FORMAT}")

    logger.debug(f"{camera.name} [{camera.host}] Disk format response: {response.text}")
    root = ElementTree.fromstring(response.content)
    job = root.find('job')
    result = job.get('result') if isinstance(job, ElementTree.Element) else None

    if result != 'OK':
        raise Exception((f"{camera.name} [{camera.host}] -  Error attempting to format to {DEFAULT_FILESYSTEM_FORMAT}"))

    logger.info(f"{camera.name} [{camera.host}] -  Formatting to {DEFAULT_FILESYSTEM_FORMAT}")
    wait_on_disk_format_job_to_complete(camera, disk_id=disk_id, job_id=job.get('jobid'))
    mount_disk(camera, action='mount', disk_id=disk_id)


def wait_on_disk_format_job_to_complete(camera: VAPIX, disk_id, job_id):
    """ Waits for the job to complete before returing """
    done = False
    while not done:
        response = camera._job_progress(params={'jobid': job_id, 'diskid': disk_id})
        logger.debug(f"{camera.name} [{camera.host}] Job progress response: {response.text}")
        root = ElementTree.fromstring(response.content)
        job = root.find('job')
        result = job.get('result') if isinstance(job, ElementTree.Element) else None
        if result == 'OK':
            percentage = job.get('progress')
            logger.info(f"{camera.name} [{camera.host}] -  Progress {percentage}%")
            done = True if percentage == "100" else time.sleep(5)
        elif result == 'ERROR':
            raise Exception(f"{camera.name} [{camera.host}] -  Error attempting to format to {DEFAULT_FILESYSTEM_FORMAT}")
    logger.info(f"{camera.name} [{camera.host}] -  Succesfully formatted filesystem {DEFAULT_FILESYSTEM_FORMAT}")


def set_zipstream_gop_settings(camera: VAPIX):
    """ 
    Update GOP to dynamic and set max gop length to fps.
    This updates for all channels.
    """
    response = camera._set_zipstream_gop(params={'schemaversion': '1', 'gopmode': 'dynamic', 'maxgoplength': '15'})
    if response and response.ok:
        logger.debug(f"{camera.name} [{camera.host}] Set zipstream gop response: {response.text}")
        root = ElementTree.fromstring(response.content)
        for child in root:
            if 'Success' in child.tag:
                logger.info(f"{camera.name} [{camera.host}] -  Successfully configured dynmaic GOP")
            if 'Error' in child.tag:
                raise Exception(f"{camera.name} [{camera.host}] -  Failed to update GOP settings")
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Failed to update GOP settings")


def set_zipstream_strength(camera: VAPIX, strength: int):
    """
    Zipstream strength 30 or higher with dynamic GOP is recommended,
    for cameras that are connected to the cloud and,
    for cameras that record to SD cards that need to limit the bit rate in order to keep recordings for a longer time.

    Parameters
    ----------
    strength: string
        - off, 10, 20, 30, 40, 50
    """
    response = camera._set_zipstream_strength(params={'schemaversion': '1', 'strength': str(strength)})
    if response and response.ok:
        logger.debug(f"{camera.name} [{camera.host}] Set zipstream strength response: {response.text}")
        root = ElementTree.fromstring(response.content)
        for child in root:
            if 'Success' in child.tag:
                logger.info(f"{camera.name} [{camera.host}] -  Successfully set zipstream strength to {strength}")
            if 'Error' in child.tag:
                raise Exception(f"{camera.name} [{camera.host}] -  Failed to update zipstream strength")
    else:
        raise Exception(f'{camera.name} [{camera.host}] Something went wrong... Failed to set zipstream strength')


def configure_textoverlays(camera: VAPIX):
    """ Checks for the textoverlay on every channel.  If channel is missing overlay then it is added. """
    payload = json.dumps({"apiVersion": "1.0", "context": "FO Configuration Managememnt", "method": "list", "params": {}})
    response = camera._text_overlay(data=payload)
    if response and response.ok:
        logger.debug(f"{camera.name} [{camera.host}] List textoverlay response: {response.text}")
        result = response.json()
        error = result.get('error')
        if error:
            raise Exception(f"{camera.name} [{camera.host}] -  Error {error.get('code')} when finding textoverlays. {error.get('message')}")
        overlays = result.get('data', {}).get('textOverlays')
        logger.info(f"{camera.name} [{camera.host}] -  Found {len(overlays)} overlays")
        channels = {overlay.get('camera') for overlay in overlays if overlay.get('text') == DEFAULT_TEXT_OVERLAY}
        for channel in range(1, 13):
            if channel in channels:
                logger.info(f"{camera.name} [{camera.host}] -  Already has text overlay set for camera channel {channel}")
            else:
                add_text_overlay(camera, channel)
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Problem finding text overlays..")

def add_text_overlay(camera: VAPIX, channel):
    """ Adds a timestamp textoverlay to every channel. """
    payload = json.dumps(
        {
            "apiVersion": "1.0",
            "context": "FO Configuration Management",
            "method": "addText",
            "params": {"camera": channel, "text": DEFAULT_TEXT_OVERLAY, "position": "topLeft", "textColor": "white"},
        }
    )
    response = camera._text_overlay(data=payload)
    if response and response.ok:
        logger.debug(f"{camera.name} [{camera.host}] Add textoverlay response: {response.text}")
        result = response.json()
        error = result.get('error')
        if error:
            raise Exception(
                f"{camera.name} [{camera.host}] -  Error {error.get('code')} when adding textoverlay to camera channel {channel}. {error.get('message')}"
            )
        else:
            logger.info(f"{camera.name} [{camera.host}] -  Successfully added text overlay for channel {channel}")
    else:
        raise Exception(f"{camera.name} [{camera.host}] -  Problem adding text overlay to camera channel {channel}")
