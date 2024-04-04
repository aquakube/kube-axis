
from typing import AsyncIterator

import kopf


class ServiceTunnel:

    def __init__(self, namespace, service_name, service_port, container_port):
        self.namespace = namespace
        self.service_name = service_name
        self.service_port = service_port
        self.container_port = container_port

    async def __call__(
        self, fn: kopf.WebhookFn
    ) -> AsyncIterator[kopf.WebhookClientConfig]:
        server = kopf.WebhookServer(
            port=self.container_port,
            host=f"{self.service_name}.{self.namespace}.svc"
        )
        async for client_config in server(fn):
            del client_config["url"]
            client_config["service"] = kopf.WebhookClientConfigService(
                name=self.service_name,
                namespace=self.namespace,
                port=self.service_port
            )
            yield client_config