import os
import kopf

from handlers import create, update, admission
from utilities.tunnel import ServiceTunnel


@kopf.on.startup()
def startup(logger, settings, **kwargs):
    """
    Execute this handler when the operator starts.
    No call to the API server is made until this handler
    completes successfully.
    """

    settings.execution.max_workers = 5
    settings.networking.request_timeout = 30
    settings.networking.connect_timeout = 10
    settings.persistence.finalizer = 'axis.aquakube.io/finalizer'
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix='axis.aquakube.io')
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(prefix='axis.aquakube.io')
    settings.admission.managed = 'axis.aquakube.io'

    # default to using a tunnel to the service. This will start ngrok.
    # You need to have kopf[dev] installed for this to work.
    if os.environ.get("ENVIRONMENT", "dev") == "dev":
        settings.admission.server = kopf.WebhookAutoTunnel()

    # if we are in production, use a service tunnel. This will use the self-signed
    # cert that is created by the operator.
    else:
        settings.admission.server = ServiceTunnel(
            namespace=os.getenv("NAMESPACE", "axis"),
            service_name=os.getenv("SERVICE_NAME"),
            service_port=int(os.getenv("SERVICE_PORT", 443)),
            container_port=int(os.getenv("CONTAINER_PORT", 9443))
        )


@kopf.on.cleanup()
def cleanup(logger, **kwargs):
    logger.info("im shutting down. Goodbye!")


@kopf.on.validate('axis')
def validateaxis(**kwargs):
    admission.validate(**kwargs)
    

@kopf.on.mutate("axis")
def mutateaxis(**kwargs):
    admission.mutate(**kwargs)


@kopf.on.create('axis')
@kopf.on.update('axis')
def on_create(body, name, namespace, logger, patch, **kwargs):
    """
    For each axis, create a workflow to provision the axis.
    It's phase will be set to provisioning.
    """
    create.workflow(name, namespace, body, logger, patch)


@kopf.on.field(
    'workflow',
    field='status.phase',
    labels={'axis.aquakube.io/name': kopf.PRESENT},
)
def on_update_workflow(old, new, body, logger, **kwargs):
    """
    When the workflow is done, update the axis status depending
    on the status of the argo workflow
    """
    axis_name = body['metadata']['labels']['axis.aquakube.io/name']

    # when the workflow was running and is now succeeded
    if old == 'Running' and new == 'Succeeded':
        update.status(
            name=axis_name,
            status={ 'phase': 'provisioned' },
            logger=logger
        )
    
    # when the workflow was running and is now failed
    elif old == 'Running' and new == 'Failed':
        update.status(
            name=axis_name,
            status={ 'phase': 'failed_provisioning' },
            logger=logger
        )
