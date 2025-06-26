import hashlib

import jwt
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import exceptions

from care.emr.models import User


def generate_password_reset_token(user):
    """Generate a JWT token with HMAC-SHA256 signature"""
    exp_time = timezone.now() + timezone.timedelta(hours=24)
    secret_key = settings.SECRET_KEY
    password_hash = hashlib.sha256((user.password + secret_key).encode()).hexdigest()
    payload = {
        "iat": int(timezone.now().timestamp()),
        "exp": int(exp_time.timestamp()),
        "sub": str(user.external_id),
        "type": "password_reset",
        "password_hash": password_hash,
        "username": user.username,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_password_reset_token(token):
    """Verify a password reset token using HMAC-SHA256"""
    secret_key = settings.SECRET_KEY
    user = None
    error_message = None

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        username = payload.get("username")
        if not username:
            error_message = "Invalid token format"
        user = User.objects.get(username=username)

        expected_password_hash = hashlib.sha256(
            (user.password + secret_key).encode()
        ).hexdigest()
        if payload.get("password_hash") != expected_password_hash:
            error_message = "Token invalid due to password change"

        if payload.get("type") != "password_reset":
            error_message = "Invalid token type"
        elif payload.get("sub") != str(user.external_id):
            error_message = "Token doesn't match user"

    except jwt.ExpiredSignatureError:
        error_message = "Invalid token"
    except User.DoesNotExist:
        error_message = "User not found"
    except Exception as e:
        error_message = f"Error verifying token: {e!s}"

    return (user, error_message) if not error_message else (None, error_message)


def send_password_reset_email(user, mail_type):
    """
    Sends the password reset email to the user.
    """
    try:
        token = generate_password_reset_token(user)
        context = {
            "current_user": user,
            "username": user.username,
            "email": user.email,
            "reset_password_url": f"{settings.CURRENT_DOMAIN}/password_reset/{token}",
        }
        if mail_type == "create_password":
            email_html_message = render_to_string(
                settings.USER_CREATE_PASSWORD_EMAIL_TEMPLATE_PATH, context
            )
            subject = "Set Up Your Password for Care"
        else:
            email_html_message = render_to_string(
                settings.USER_RESET_PASSWORD_EMAIL_TEMPLATE_PATH, context
            )
            subject = "Password Reset for Care"
        msg = EmailMessage(
            subject,
            email_html_message,
            settings.DEFAULT_FROM_EMAIL,
            (user.email,),
        )
        msg.content_subtype = "html"
        msg.send()

    except ValidationError as e:
        raise exceptions.ValidationError({"message": e.messages}) from e
