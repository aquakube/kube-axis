import time
import logging

from axis.configure import configure
from utilities.state import load

logger = logging.getLogger()


def run(resource: dict):
    """
    Configure the AXIS device with the provided video stream settings.
    """
    time.sleep(15) # noop sleep to wait for provisioning changes to sink in.  transient issues can occure when network interface configuration mode is changed
    configure(resource, state=load())