import os
import logging

from utilities.state import load
from utilities.command import run_command, is_reachable
from utilities.vapix import VAPIX

logger = logging.getLogger(__name__)


def get_sample_image(ip_address: str):
    """
    Gets a sample image from the AXIS device at the provided ip_address
    """

    logger.info("Getting sample image from AXIS device")

    pipeline = f"""
    ffmpeg \
        -y \
        -i \
        'rtsp://{ip_address}:554/axis-media/media.amp?resolution=720x720&FPS=15&h264profile=high&videobitratemode=vbr&videocodec=h264&camera=1' \
        -vframes 1 \
        /tmp/output.png
    """

    run_command(pipeline)

    if not os.path.exists('/tmp/output.png'):
        raise Exception(f"Could not create sample image from AXIS device at IP address: {ip_address}")


def run(resource: dict):

    state = load()

    camera = VAPIX(
        name=resource['metadata']['name'],
        host=state['ip_address'],
        username='root',
        password='admin'
    )

    # TODO: add camera verification logic here
