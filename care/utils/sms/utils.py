from typing import TYPE_CHECKING

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from care.utils.sms.message import TextMessage

if TYPE_CHECKING:
    from care.utils.sms.backend.base import SmsBackendBase


def get_sms_content(template_path: str, context: dict) -> str:
    try:
        return render_to_string(template_path, context)
    except TemplateDoesNotExist:
        error = f"Template '{template_path}' not found."
        raise TemplateDoesNotExist(error) from error


def initialize_backend(
    backend_name: str | None = None, fail_silently: bool = False, **kwargs
) -> "SmsBackendBase":
    """
    Load and configure an SMS backend.

    Args:
        backend_name (Optional[str]): The dotted path to the backend class. If None, the default backend from settings is used.
        fail_silently (bool): Whether to handle exceptions quietly. Defaults to False.

    Returns:
        SmsBackendBase: An initialized instance of the specified SMS backend.
    """
    backend_class = import_string(backend_name or settings.SMS_BACKEND)
    return backend_class(fail_silently=fail_silently, **kwargs)


def send_text_message(
    content: str = "",
    sender: str | None = None,
    recipients: str | list[str] | None = None,
    fail_silently: bool = False,
    backend_instance: type["SmsBackendBase"] | None = None,
) -> int:
    """
    Send a single SMS message to one or more recipients.

    Args:
        content (str): The message content to be sent. Defaults to an empty string.
        sender (Optional[str]): The sender's phone number. Defaults to None.
        recipients (Union[str, List[str], None]): A single recipient or a list of recipients. Defaults to None.
        fail_silently (bool): Whether to suppress exceptions during sending. Defaults to False.
        backend_instance (Optional[SmsBackendBase]): A pre-configured SMS backend instance. Defaults to None.

    Returns:
        int: The number of messages successfully sent.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    message = TextMessage(
        content=content,
        sender=sender,
        recipients=recipients,
        backend=backend_instance,
        fail_silently=fail_silently,
    )
    return message.dispatch(fail_silently=fail_silently)


def get_sms_backend(
    backend_name: str | None = None, fail_silently: bool = False, **kwargs
) -> "SmsBackendBase":
    """
    Load and return an SMS backend instance.

    Args:
        backend_name (Optional[str]): The dotted path to the backend class. If None, the default backend from settings is used.
        fail_silently (bool): Whether to suppress exceptions quietly. Defaults to False.
        **kwargs: Additional arguments passed to the backend constructor.

    Returns:
        SmsBackendBase: An initialized instance of the specified SMS backend.
    """
    return initialize_backend(
        backend_name=backend_name or settings.SMS_BACKEND,
        fail_silently=fail_silently,
        **kwargs,
    )
