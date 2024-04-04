import os
import yaml

import kopf
from jinja2 import Template
from kubernetes import client

from utilities.jinja import load_workflow_template

def workflow(name, namespace, body, logger, patch):
    """
    Create a workflow for provisioning
    """
    logger.info("Creating workflow")

    api = client.CustomObjectsApi()

    template: Template = load_workflow_template()

    version = body['spec']['workflow']['version']

    rendered_template = template.render(
        name=name,
        image=f"456087932636.dkr.ecr.us-west-2.amazonaws.com/kube-axis/workflow:{version}",
        google_webhook=os.getenv("GOOGLE_WEBHOOK"),
        slack_webhook=os.getenv("SLACK_WEBHOOK"),
        firmware_allow_list=os.getenv("FIRMWARE_ALLOW_LIST"),
        firmware_deny_list=os.getenv("FIRMWARE_DENY_LIST"),
        resource={
            'apiVersion': body['apiVersion'],
            'kind': body['kind'],
            'metadata': {
                'name': body['metadata']['name'],
                'namespace': body['metadata']['namespace'],
                'labels': body['metadata'].get('labels', []),
            },
            'spec': body['spec'],
        },
    )

    workflow = yaml.safe_load(rendered_template)

    kopf.label(
        objs=[workflow],
        labels={
            'app.kubernetes.io/name': name,
            'app.kubernetes.io/instance': f"{namespace}.{name}",
            'app.kubernetes.io/version': f"{version}",
            'app.kubernetes.io/component': 'axis',
            'app.kubernetes.io/part-of': 'aquakube',
            'app.kubernetes.io/managed-by': 'axis-operator'
        },
        nested='spec.template'
    )

    api.create_namespaced_custom_object(
        group="argoproj.io",
        version="v1alpha1",
        namespace="argo",
        plural="workflows",
        body=workflow,
    )

    patch.status['phase'] = 'provisioning'