
import time
import os
import json
import sys
import logging
import argparse
from ast import literal_eval

from steps import discover, provision, configure, verify, notify
from utilities.logger import setup_logger

def required_env(key) -> str:
    """
    Retrieves the key from the os.getenv() method. If
    the value is None, raises an Exception.
    """
    value = os.getenv(key)
    if value is None:
        raise Exception(f'{key} is a required environment variable. Cannot be None')
    
    return value


def execute_step(step_function, *args, **kwargs):
    try:
        step_function(*args, **kwargs)
    except Exception as e:

        state = {}

        if os.path.exists('/tmp/state.json'):
            with open('/tmp/state.json', 'r') as f:
                state = json.loads(f.read())

        state['error'] = f"""
AXIS provisioning failed due to an exception.
exception: {e}
        """

        with open('/tmp/state.json', 'w') as f:
            f.write(json.dumps(state))

        raise e


if __name__ == "__main__":
    """
    AXIS Workflow engine. This script is responsible for executing the workflow steps.
    """
    setup_logger()
    logger = logging.getLogger()

    parser = argparse.ArgumentParser()
    parser.add_argument('--command', type=str, required=True, help='Command to run: discover, provision, verify')
    args = parser.parse_args()
    
    commands = ['discover', 'provision', 'configure', 'verify', 'notify']

    if args.command not in commands:
        logger.error('Command must be one of: %s', ', '.join(commands))
        exit(1)

    resource = literal_eval(required_env('RESOURCE'))

    if args.command == 'discover':
        execute_step(discover.run, resource)
    
    elif args.command == 'provision':
        execute_step(provision.run, resource)

    elif args.command == 'configure':
        execute_step(configure.run, resource)

    elif args.command == 'verify':
        execute_step(verify.run, resource)

    elif args.command == 'notify':
        notify.run(resource)

    else:
        logger.error('Command must be one of: %s', ', '.join(commands))
        exit(1)

    exit(0)
