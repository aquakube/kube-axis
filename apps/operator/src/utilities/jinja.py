import os

from jinja2 import Template, StrictUndefined


def load_template(path: str) -> Template:
    """
    Loads a jinja2 template from a file
    """
    with open(path, 'rt') as f:
        return Template(f.read(), undefined=StrictUndefined)


def load_workflow_template() -> Template:
    """
    Loads the workflow template for provisioning
    """
    if os.getenv("ENVIRONMENT", "dev") == "dev":
        path = './apps/operator/kubernetes/provision.yaml'
    else:
        path = '/usr/app/kubernetes/provision.yaml'

    return load_template(path)
