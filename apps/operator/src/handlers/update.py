from kubernetes import client
from kubernetes.client.exceptions import ApiException


def status(
    name,
    status,
    group="aquakube.io",
    version="v1",
    plural="axis",
    logger=None
):
    """
    Update the CRs status to reflect workflow progress / results
    TODO: define status schema
    """
    api = client.CustomObjectsApi()
    try:
        api.patch_namespaced_custom_object_status(
            group=group,
            version=version,
            namespace='axis',
            plural=plural,
            name=name,
            body={'status': status}
        )
    except ApiException as e:
        logger.exception(f"Failed to update axis status")