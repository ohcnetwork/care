import sys
import threading

from care.utils.sms.backend.base import SmsBackendBase
from care.utils.sms.message import TextMessage


class ConsoleBackend(SmsBackendBase):
    """
    Outputs SMS messages to the console for debugging purposes.
    """

    def __init__(self, *args, stream=None, **kwargs) -> None:
        """
        Initialize the ConsoleBackend.

        Args:
            stream (Optional[TextIO]): The output stream to write messages to. Defaults to sys.stdout.
            *args: Additional arguments for the superclass.
            **kwargs: Additional keyword arguments for the superclass.
        """
        super().__init__(*args, **kwargs)
        self.stream = stream or sys.stdout
        self._lock = threading.RLock()

    def send_message(self, message: TextMessage) -> int:
        """
        Write the SMS message to the console.

        Args:
            message (TextMessage): The message to be sent.

        Returns:
            int: The number of messages successfully "sent" (i.e., written to the console).
        """
        sent_count = 0
        with self._lock:
            for recipient in message.recipients:
                self.stream.write(
                    f"From: {message.sender}\nTo: {recipient}\nContent: {message.content}\n{'-' * 100}\n"
                )
                sent_count += 1
            self.stream.flush()
        return sent_count
