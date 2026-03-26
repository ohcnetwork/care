from abc import ABC, abstractmethod


class BaseMessagingProvider(ABC):
    @abstractmethod
    def send_message(self, recipient_id: str, message: str, **kwargs) -> None:
        """
        Send a message to a recipient.
        """
        pass

    @abstractmethod
    def handle_webhook(self, data: dict) -> None:
        """
        Handle an incoming webhook from the provider.
        """
        pass
