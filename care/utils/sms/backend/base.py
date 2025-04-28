from care.utils.sms.message import TextMessage


class SmsBackendBase:
    """
    Base class for all SMS backends.

    Subclasses should override the `send_message` method to provide the logic
    for sending SMS messages.
    """

    def __init__(self, fail_silently: bool = False, **kwargs) -> None:
        """
        Initialize the SMS backend.

        Args:
            fail_silently (bool): Whether to suppress exceptions during message sending. Defaults to False.
            **kwargs: Additional arguments for backend configuration.
        """
        self.fail_silently = fail_silently

    def send_message(self, message: TextMessage) -> int:
        """
        Send a text message.

        Subclasses must implement this method to handle the logic for sending
        messages using the specific backend.

        Args:
            message (TextMessage): The message to be sent.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.

        Returns:
            int: The number of messages successfully sent.
        """
        raise NotImplementedError("Subclasses must implement `send_message`.")
