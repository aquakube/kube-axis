import logging

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger(__name__)


class VAPIX:
    """
    VAPIX Network video APIs is a set of application programming interfaces (APIs) for configuration and management of Axis network video products.
    For more information visit https://www.axis.com/vapix-library/

    Note:
    When debugging server side errors a list of system event logs can be found here http://<your-axis-cam-ip>/axis-cgi/admin/systemlog.cgi
    """

    def __init__(self, name: str, host: str, username: str = None, password: str = None, timeout=None):
        self.name = name
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.stream_profile_cgi = f"http://{host}/axis-cgi/streamprofile.cgi"
        self.disk_management_list_cgi = f"http://{host}/axis-cgi/disks/list.cgi"
        self.zipstream_setgop_cgi = f"http://{host}/axis-cgi/zipstream/setgop.cgi"
        self.zipstream_setstrength_cgi = f"http://{host}/axis-cgi/zipstream/setstrength.cgi"
        self.textoverlay_cgi = f"http://{host}/axis-cgi/dynamicoverlay/dynamicoverlay.cgi"
        self.record_export_cgi = f"http://{host}/axis-cgi/record/export/exportrecording.cgi"
        self.record_remove_cgi = f"http://{host}/axis-cgi/record/remove.cgi"
        self.record_list_cgi = f"http://{host}/axis-cgi/record/list.cgi"
        self.disk_format_cgi = f"http://{host}/axis-cgi/disks/format.cgi"
        self.job_progress_cgi = f"http://{host}/axis-cgi/disks/job.cgi"
        self.disk_mount_cgi = f"http://{host}/axis-cgi/disks/mount.cgi"
        self.params_cgi = f"http://{host}/axis-cgi/param.cgi"
        self.firmware_management_cgi = f"http://{host}/axis-cgi/firmwaremanagement.cgi"
        self.firmware_upgrade_cgi = f"http://{host}/axis-cgi/firmwareupgrade.cgi?type=normal"
        self.ntp_cgi = f"http://{host}/axis-cgi/ntp.cgi"
        self.pwdgrp_cgi = f"http://{host}/axis-cgi/pwdgrp.cgi"
        self.network_settings_cgi = f"http://{host}/axis-cgi/network_settings.cgi"


    def _list_disks(self, params):
        """ Use disks/list.cgi to retrieve information about available disks and their status. An available disk is mounted and ready to be used."""
        logger.debug(f"VAPIX [{self.host}] Performing disk check to retrieve information about available disks and their status.")
        return self.request('GET', self.disk_management_list_cgi, params=params)


    def _list_recordings(self, params):
        """ The record/list.cgi is used to search for recordings and list information about found recordings. """
        logger.debug(f"VAPIX [{self.host}] Performing search for recordings and information about found recordings.")
        return self.request('GET', self.record_list_cgi, params=params)


    def _set_zipstream_gop(self, params):
        """
        Use zipstream/setgop.cgi to set the GOP mode and the maximum GOP length. 
        The GOP settings can be set on all video channels or on an individual video channel. 
        The new settings will be used for new streams, ongoing streams will not be affected. 
        """
        logger.debug(f"VAPIX [{self.host}] Setting the Zipstream GOP mode and the maximum GOP length.")
        return self.request('GET', self.zipstream_setgop_cgi, params=params)


    def _set_zipstream_strength(self, params):
        """
        Use zipstream/setstrength.cgi to set the Zipstream strength. 
        The strength can be set on all video channels or on an individual channel. 
        The new strength will be used for new streams, ongoing streams will not be affected.
        """
        logger.debug(f"VAPIX [{self.host}] Setting the Zipstream strength")
        return self.request('GET', self.zipstream_setstrength_cgi, params=params)


    def _text_overlay(self, data):
        """
        List all overlays previously created by add methods.
        Add mehtod creates a text overlay and returns an overlay ID if successful, otherwise returns an error
        """
        logger.debug(f"VAPIX [{self.host}] Performing text overlay operation")
        return self.request(method='POST', url=self.textoverlay_cgi, data=data)


    def _remove_recording(self, params):
        """ The record/remove.cgi is used to remove one or more recordings. """
        logger.debug(f"VAPIX [{self.host}] Performing operation to remove one or more recordings.")
        return self.request(method='GET', url=self.record_remove_cgi, params=params)


    def _stream_profile(self, data):
        """
        This API method can be used to add a new stream profile.
        The name of each stream profile needs to be unique, otherwise, an error will be returned.
        """
        logger.debug(f"VAPIX [{self.host}] Performing stream profile operation")
        return self.request(method='POST', url=self.stream_profile_cgi, data=data)


    def _format_disk(self, params):
        """ Use disks/format.cgi format disks. SD cards can be formatted with ext4 or vfat. """
        logger.debug(f"VAPIX [{self.host}] Formatting SD card")
        return self.request(method='GET', url=self.disk_format_cgi, params=params)


    def _job_progress(self, params):
        """ Use disks/job.cgi to check the progress of a format, check disk, repair, mount or unmount job. """
        logger.debug(f"VAPIX [{self.host}] Checking job progress of a format, check disk, repair, mount or unmount job.")
        return self.request(method='GET', url=self.job_progress_cgi, params=params)


    def _disk_mount(self, params):
        """
        Use disks/mount.cgi to mount a disk to the system and to unmount a disk from the system.
        To prevent corruption of recordings, SD cards should always be unmounted before being ejected.
        """
        logger.debug(f"VAPIX [{self.host}] Performing operation to mount a disk to the system and/or to unmount a disk from the system")
        return self.request(method='GET', url=self.disk_mount_cgi, params=params)


    def _parameter_management(self, method, params):
        """
        To handle the parameters of an Axis product you need to request the CGI param.cgi. 
        This needs to be followed by the argument action and a valid value.
        method: GET/POST
        """
        logger.debug(f"VAPIX [{self.host}] Parameter mangement")
        return self.request(method=method, url=self.params_cgi, params=params)


    def _firmware_management(self, method, params=None, data=None, files=None, mp=None):
        """
        Firmware management API describes how to manage the firmware of the Axis products in order to:
            - Retrieve the status for the current firmware.
            - Upgrade the firmware.
            - Rollback firmware to the previously installed version.
            - Restore configurations back to the factory defaults.
            - Reboot the Axis product.
        method: GET/POST
        """
        logger.debug(f"VAPIX [{self.host}] Firmware management")
        return self.request(method=method, url=self.firmware_management_cgi, params=params, data=data)


    def _upgrade_firmware(self, data):
        """
        Upgrade the firmware
        
        Parameters
        ----------
        data: firmware file content
        """
        logger.debug(f"VAPIX [{self.host}] Upgrading firmware")
        return self.request(method='POST', url=self.firmware_upgrade_cgi, headers={'Content-Type': 'application/octet-stream'}, data=data)


    def _ntp_client(self, data):
        """
        Configures the axis cam to synchronize its internal clock and date by using NTP.
        Note: This CGI replaces param.cgi by offering an updated way to configure and retrieve data for NTP related parameters.
        Firmware: 9.10 and later   
        """
        logger.debug(f"VAPIX [{self.host}] Configuring NTP cleint")
        return self.request(method='POST', url=self.ntp_cgi, data=data)


    def _user_management(self, params):
        """ The pwdgrp.cgi is used to add a new user account with password and group membership, modify the information and remove a user account. """
        logger.debug(f"VAPIX [{self.host}] User management - add, modify, list, and delete user accounts")
        return self.request(method="GET", url=self.pwdgrp_cgi, params=params)


    def _network_settings(self, data):
        """ The Network settings API makes it possible to configure network related functionality on an Axis device """
        logger.debug(f"VAPIX [{self.host}] Performing network settings operation")
        return self.request(method='POST', url=self.network_settings_cgi, data=data)


    def request(self, method, url, headers={'Content-Type': 'application/json'}, params=None, data=None):
        """
        Parameters
        ----------
        method: string
            - GET, OPTIONS, HEAD, POST, PUT, PATCH, or DELETE
        url: string
        headers: dict
        params: dict
        data: json

        Returns:
        --------
        HTTPResponse
        Content-type: text/xml video/x-matroska
        HTTP code: 200 OK
        Content-disposition: attachment; filename="[YYYYMMDD_HHMMSSMMMM_YYYYMMDD_HHMMSSMMMM.mkv]"
        """
        response = None
        try:
            response = requests.request(
                method,
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                headers=headers,
                data=data,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.ConnectionError:
            logger.exception(f"[{self.host}] The cgi request failed to connect with exception")
        except requests.exceptions.Timeout:
            logger.exception(f"[{self.host}] The cgi request timed out")
        except Exception:
            logger.exception(f"[{self.host}] The cgi request failed with exception:")
        return response


    def _export(self, recording_id):
        """ Use record/export/exportrecording.cgi to export a recording. """
        logger.debug(f"VAPIX [{self.host}] Exporting recording")
        return requests.get(
            self.record_export_cgi,
            stream=True,
            timeout=self.timeout,
            params={
                "schemaversion": 1,
                "recordingid": recording_id,
                "diskid": "SD_DISK",
                "exportformat": "matroska",
            }
        )
