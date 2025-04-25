from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from care.emr.utils.file_manager import FileManager
from care.utils.csp.config import get_client_config


class AzureFileManager(FileManager):
    """Utility class for managing files in Azure Blob Storage."""

    bucket_type = None

    def __init__(self, bucket_type):
        """Initialize with bucket type for configuration."""
        self.bucket_type = bucket_type

    def _get_blob_service_client(self, external=False):
        """Get Azure Blob Service client and container name."""
        config, container_name = get_client_config(self.bucket_type, external=external)
        connection_string = config.get("connection_string")
        if not connection_string:
            raise ValueError("Azure connection string is required in config")

        return BlobServiceClient.from_connection_string(
            connection_string
        ), container_name

    def signed_url(self, file_obj, duration=60 * 60, mime_type=None):
        """Generate signed URL for uploading a file."""
        service_client, container_name = self._get_blob_service_client(external=True)
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=f"{file_obj.file_type}/{file_obj.internal_name}",
        )

        sas_token = generate_blob_sas(
            account_name=service_client.account_name,
            container_name=container_name,
            blob_name=f"{file_obj.file_type}/{file_obj.internal_name}",
            account_key=service_client.credential.account_key,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.now(tz=ZoneInfo("UTC")) + timedelta(seconds=duration),
        )

        url = f"{blob_client.url}?{sas_token}"
        if mime_type or file_obj.meta.get("mime_type"):
            url += f"&content_type={mime_type or file_obj.meta.get('mime_type')}"

        return url

    def read_signed_url(self, file_obj, duration=60 * 60):
        """Generate signed URL for downloading a file."""
        service_client, container_name = self._get_blob_service_client(external=True)
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=f"{file_obj.file_type}/{file_obj.internal_name}",
        )

        sas_token = generate_blob_sas(
            account_name=service_client.account_name,
            container_name=container_name,
            blob_name=f"{file_obj.file_type}/{file_obj.internal_name}",
            account_key=service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(tz=ZoneInfo("UTC")) + timedelta(seconds=duration),
        )

        url = f"{blob_client.url}?{sas_token}"
        url += f"&response-content-disposition=attachment; filename={file_obj.name}{file_obj.get_extension()}"
        return url

    def put_object(self, file_obj, file, **kwargs):
        """Upload a file to Azure Blob Storage."""
        service_client, container_name = self._get_blob_service_client()
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=f"{file_obj.file_type}/{file_obj.internal_name}",
        )

        content_type = kwargs.pop("ContentType", None)
        if content_type:
            kwargs["content_type"] = content_type

        return blob_client.upload_blob(data=file, overwrite=True, **kwargs)

    def get_object(self, file_obj, **kwargs):
        """Get a file from Azure Blob Storage."""
        service_client, container_name = self._get_blob_service_client()
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=f"{file_obj.file_type}/{file_obj.internal_name}",
        )

        return blob_client.download_blob(**kwargs)

    def file_contents(self, file_obj):
        """Get file contents and content type."""
        response = self.get_object(file_obj)
        content_type = response.content_settings.content_type
        content = response.readall()
        return content_type, content
