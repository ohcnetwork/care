from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_rest_passwordreset.models import ResetPasswordToken

User = get_user_model()


def send_password_creation_email(instance: User, fail_silently=False):
    if instance.password_reset_tokens.all().count() > 0:
        # yes, already has a token, re-use this token
        reset_password_token = instance.password_reset_tokens.all()[0]
    else:
        # no token exists, generate a new token
        reset_password_token = ResetPasswordToken.objects.create(
            user=instance,
        )
    context = {
        "current_user": reset_password_token.user,
        "username": reset_password_token.user.username,
        "email": reset_password_token.user.email,
        "create_password_url": f"{settings.CURRENT_DOMAIN}/password_reset/{reset_password_token.key}",
    }
    email_html_message = render_to_string(
        settings.USER_CREATE_PASSWORD_EMAIL_TEMPLATE_PATH, context
    )
    msg = EmailMessage(
        "Set Up Your Password for Care",
        email_html_message,
        settings.DEFAULT_FROM_EMAIL,
        (reset_password_token.user.email,),
    )
    msg.content_subtype = "html"
    msg.send(fail_silently=fail_silently)
