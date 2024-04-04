import json


def load(file: str = '/tmp/state.json') -> dict:
    """
    Loads state from a file
    """
    state = {}
    with open(file, 'r') as f:
        state = json.load(f)
    return state


def save(state: dict, file: str = '/tmp/state.json'):
    """
    Saves state to a file
    """
    with open(file, 'w') as f:
        json.dump(state, f)