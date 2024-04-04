import logging

from axis.provision import provision
from utilities.state import save, load

logger = logging.getLogger()


def run(resource: dict):
    """
    Provisions the AXIS device with the provided network settings.
    """
    save(state=provision(resource, state=load()))