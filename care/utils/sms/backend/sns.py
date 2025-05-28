from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from care.utils.sms.backend.base import SmsBackendBase
from care.utils.sms.message import TextMessage

try:
    import boto3
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class SnsBackend(SmsBackendBase):
    """
    Sends SMS messages using AWS SNS.
    """

    _sns_client = None

    @classmethod
    def _get_client(cls):
        """
        Get or create the SNS client.

        Returns:
            boto3.Client: The shared SNS client.
        """
        if cls._sns_client is None:
            region_name = getattr(settings, "SNS_REGION", None)

            if not HAS_BOTO3:
                raise ImproperlyConfigured(
                    "Boto3 library is required but not installed."
                )

            if getattr(settings, "SNS_ROLE_BASED_MODE", False):
                if not region_name:
                    raise ImproperlyConfigured(
                        "AWS SNS is not configured. Check 'SNS_REGION' in settings."
                    )
                cls._sns_client = boto3.client(
                    "sns",
                    region_name=region_name,
                )
            else:
                access_key_id = getattr(settings, "SNS_ACCESS_KEY", None)
                secret_access_key = getattr(settings, "SNS_SECRET_KEY", None)
                if not region_name or not access_key_id or not secret_access_key:
                    raise ImproperlyConfigured(
                        "AWS SNS credentials are not fully configured. Check 'SNS_REGION', 'SNS_ACCESS_KEY', and 'SNS_SECRET_KEY' in settings."
                    )
                cls._sns_client = boto3.client(
                    "sns",
                    region_name=region_name,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                )
        return cls._sns_client

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        """
        Initialize the SNS backend.

        Args:
            fail_silently (bool): Whether to suppress exceptions during initialization. Defaults to False.
            **kwargs: Additional arguments for backend configuration.
        """
        super().__init__(fail_silently=fail_silently, **kwargs)

    def send_message(self, message: TextMessage) -> int:
        """
        Send a text message using AWS SNS.

        Args:
            message (TextMessage): The message to be sent.

        Returns:
            int: The number of messages successfully sent.
        """
        sns_client = self._get_client()
        successful_sends = 0

        for recipient in message.recipients:
            try:
                sns_client.publish(
                    PhoneNumber=recipient,
                    Message=message.content,
                )
                successful_sends += 1
            except ClientError as error:
                if not self.fail_silently:
                    raise error
        return successful_sends
