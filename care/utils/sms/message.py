from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from care.utils.sms.backend.base import SmsBackendBase


class TextMessage:
    """
    Represents a text message for transmission to one or more recipients.
    """

    def __init__(
        self,
        content: str = "",
        sender: str | None = None,
        recipients: list[str] | None = None,
        backend: type["SmsBackendBase"] | None = None,
        fail_silently: bool = False,
    ) -> None:
        """
        Initialize a TextMessage instance.

        Args:
            content (str): The message content.
            sender (Optional[str]): The sender's phone number.
            recipients (Optional[List[str]]): List of recipient phone numbers.
            backend (Optional[SmsBackendBase]): Backend for sending the message.
        """
        self.content = content
        self.sender = sender or getattr(settings, "DEFAULT_SMS_SENDER", "")
        self.recipients = recipients or []
        self.backend = backend

        if not self.backend:
            from care.utils.sms import get_sms_backend

            self.backend = get_sms_backend(fail_silently=fail_silently)

        if isinstance(self.recipients, str):
            raise ValueError("Recipients should be a list of phone numbers.")

    def dispatch(self, fail_silently: bool = False) -> int:
        """
        Send the message to all designated recipients.

        Args:
            fail_silently (bool): Whether to suppress errors during message sending.

        Returns:
            int: Count of successfully sent messages.
        """
        if not self.recipients:
            return 0

        connection = self.backend
        return connection.send_message(self)
