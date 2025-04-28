from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    expires=10 * 60,
)
def send_totp_enabled_email(user_email: str, user_name: str):
    """Send email notification when TOTP is enabled"""
    context = {
        "username": user_name,
        "email": user_email,
        "enabled_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    email_html_message = render_to_string(
        settings.TOTP_ENABLED_EMAIL_TEMPLATE_PATH, context
    )

    msg = EmailMessage(
        "Two-Factor Authentication Enabled",
        email_html_message,
        settings.DEFAULT_FROM_EMAIL,
        (user_email,),
    )
    msg.content_subtype = "html"
    msg.send()


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    expires=10 * 60,
)
def send_totp_disabled_email(user_email: str, user_name: str):
    """Send email notification when TOTP is disabled"""
    context = {
        "username": user_name,
        "email": user_email,
        "disabled_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    email_html_message = render_to_string(
        settings.TOTP_DISABLED_EMAIL_TEMPLATE_PATH, context
    )

    msg = EmailMessage(
        "Two-Factor Authentication Disabled",
        email_html_message,
        settings.DEFAULT_FROM_EMAIL,
        (user_email,),
    )
    msg.content_subtype = "html"
    msg.send()
