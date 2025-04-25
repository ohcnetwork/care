from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import boto3
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas
from django.conf import settings

from care.utils.csp.config import BucketType, CSProvider, get_client_config


class FileManager:
    """
    A utility class to manage all file management related operations
    """


class S3FilesManager(FileManager):
    bucket_type = None

    def __init__(self, bucket_type):
        self.bucket_type = bucket_type

    def signed_url(self, file_obj, duration=60 * 60, mime_type=None):
        config, bucket_name = get_client_config(self.bucket_type, external=True)
        s3 = boto3.client("s3", **config)
        params = {
            "Bucket": bucket_name,
            "Key": f"{file_obj.file_type}/{file_obj.internal_name}",
        }

        _mime_type = file_obj.meta.get("mime_type") or mime_type
        if _mime_type:
            params["ContentType"] = _mime_type
        return s3.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=duration,  # seconds
        )

    def read_signed_url(self, file_obj, duration=60 * 60):
        config, bucket_name = get_client_config(self.bucket_type, external=True)
        s3 = boto3.client("s3", **config)
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": f"{file_obj.file_type}/{file_obj.internal_name}",
                "ResponseContentDisposition": f"attachment; filename={file_obj.name}{file_obj.get_extension()}",
            },
            ExpiresIn=duration,  # seconds
        )

    def put_object(self, file_obj, file, **kwargs):
        config, bucket_name = get_client_config(self.bucket_type)
        s3 = boto3.client("s3", **config)
        return s3.put_object(
            Body=file,
            Bucket=bucket_name,
            Key=f"{file_obj.file_type}/{file_obj.internal_name}",
            **kwargs,
        )

    def get_object(self, file_obj, **kwargs):
        config, bucket_name = get_client_config(self.bucket_type)
        s3 = boto3.client("s3", **config)
        return s3.get_object(
            Bucket=bucket_name,
            Key=f"{file_obj.file_type}/{file_obj.internal_name}",
            **kwargs,
        )

    def file_contents(self, file_obj):
        response = self.get_object(file_obj)
        content_type = response["ContentType"]
        content = response["Body"].read()
        return content_type, content

    def _put_object(self, key, file):
        config, bucket_name = get_client_config(self.bucket_type)
        s3 = boto3.client("s3", **config)
        boto_params = {
            "Bucket": bucket_name,
            "Key": key,
            "Body": file,
        }
        if self.bucket_type == BucketType.FACILITY and settings.BUCKET_HAS_FINE_ACL:
            boto_params["ACL"] = "public-read"
        return s3.put_object(**boto_params)

    def _delete_object(self, key):
        config, bucket_name = get_client_config(self.bucket_type)
        s3 = boto3.client("s3", **config)
        return s3.delete_object(
            Bucket=bucket_name,
            Key=key,
        )


class AzureFileManager(FileManager):
    """Utility class for managing files in Azure Blob Storage."""

    bucket_type = None

    def __init__(self, bucket_type):
        """Initialize with bucket type for configuration."""
        self.bucket_type = bucket_type

    def _get_blob_service_client(self):
        """Get Azure Blob Service client and container name."""
        config, container_name = get_client_config(self.bucket_type, external=True)
        connection_string = config.get("aws_secret_access_key")
        if not connection_string:
            raise ValueError("Azure connection string is required in config")

        return BlobServiceClient.from_connection_string(
            connection_string
        ), container_name

    def signed_url(self, file_obj, duration=60 * 60, mime_type=None):
        """Generate signed URL for uploading a file."""
        service_client, container_name = self._get_blob_service_client()
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
        service_client, container_name = self._get_blob_service_client()
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

    def _put_object(self, key, file):
        """Upload a file to Azure Blob Storage."""
        service_client, container_name = self._get_blob_service_client()
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=key,
        )
        return blob_client.upload_blob(data=file, overwrite=True)

    def _delete_object(self, key):
        """Delete a file from Azure Blob Storage."""
        service_client, container_name = self._get_blob_service_client()
        blob_client = service_client.get_blob_client(
            container=container_name,
            blob=key,
        )
        return blob_client.delete_blob()


def get_file_manager(bucket_type: BucketType) -> FileManager:
    """
    Factory function to get the appropriate file manager based on the bucket type.
    """
    if CSProvider.AZURE.name == settings.BUCKET_PROVIDER:
        return AzureFileManager(bucket_type)
    return S3FilesManager(bucket_type)
