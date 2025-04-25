#!/usr/bin/env python3

import logging
from time import sleep

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


def create_container(
    service_client: BlobServiceClient, container_name: str
) -> ContainerClient:
    container_client = service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass
    return container_client


if __name__ == "__main__":
    # Connect to the localhost emulator (after 5 secs to make sure it's up).
    sleep(5)
    blob_service_client = BlobServiceClient(
        account_url="http://localhost:10000/devstoreaccount1",
        credential={
            "account_name": "devstoreaccount1",
            "account_key": (
                "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
                "/K1SZFPTOtr/KBHBeksoGMGw=="
            ),
        },
    )

    containers = [
        "patient-bucket",
        "facility-bucket",
    ]
    for container in containers:
        _containers = create_container(blob_service_client, container)
        logger.info(container, "created")
