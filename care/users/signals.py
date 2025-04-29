import contextlib

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.timezone import now
from django_rest_passwordreset.signals import reset_password_token_created

from .models import UserFacilityAllocation


@receiver(reset_password_token_created)
def password_reset_token_created(
    sender, instance, reset_password_token, *args, **kwargs
):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    """
    # send an e-mail to the user
    context = {
        "current_user": reset_password_token.user,
        "username": reset_password_token.user.username,
        "email": reset_password_token.user.email,
        "reset_password_url": f"{settings.CURRENT_DOMAIN}/password_reset/{reset_password_token.key}",
    }

    # render email text
    email_html_message = render_to_string(
        settings.USER_RESET_PASSWORD_EMAIL_TEMPLATE_PATH, context
    )

    msg = EmailMessage(
        "Password Reset for Care",
        email_html_message,
        settings.DEFAULT_FROM_EMAIL,
        (reset_password_token.user.email,),
    )
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send()


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def save_fields_before_update(sender, instance, raw, using, update_fields, **kwargs):
    if raw:
        return

    if instance.pk:
        fields_to_save = {"home_facility"}
        if update_fields:
            fields_to_save &= set(update_fields)
        if fields_to_save:
            with contextlib.suppress(IndexError):
                instance._previous_values = instance.__class__._base_manager.filter(  # noqa SLF001
                    pk=instance.pk
                ).values(*fields_to_save)[0]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def track_user_facility_allocation(
    sender, instance, created, raw, using, update_fields, **kwargs
):
    if raw or (update_fields and "home_facility" not in update_fields):
        return

    if created and instance.home_facility:
        UserFacilityAllocation.objects.create(
            user=instance, facility=instance.home_facility
        )
        return

    last_home_facility = getattr(instance, "_previous_values", {}).get("home_facility")

    if (
        last_home_facility and instance.home_facility_id != last_home_facility
    ) or instance.deleted:
        # this also includes the case when the user's new home facility is set to None
        UserFacilityAllocation.objects.filter(
            user=instance, facility=last_home_facility, end_date__isnull=True
        ).update(end_date=now())

    if instance.home_facility_id and instance.home_facility_id != last_home_facility:
        # create a new allocation if new home facility is changed
        UserFacilityAllocation.objects.create(
            user=instance, facility=instance.home_facility
        )
