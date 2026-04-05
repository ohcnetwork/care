import logging
import sys
from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from rest_framework.test import APIClient

import care.emr.utils.valueset_coding_type  # noqa: F401

from .base import CareFixtureBase

sys.modules["care.emr.utils.valueset_coding_type"].validate_valueset = lambda f, s, c: c


class _NoOpLock:
    """Bypass PatientCreateLock inside an outer transaction."""

    def acquire(self):
        pass

    def release(self):
        pass


@contextmanager
def care_fixture_context():
    audit_logger = logging.getLogger("audit_log")
    original_level = audit_logger.level
    audit_logger.setLevel(logging.WARNING)

    try:
        call_command("sync_permissions_roles")
        call_command("sync_valueset")

        with (
            transaction.atomic(),
            patch("care.emr.api.viewsets.patient.PatientCreateLock", _NoOpLock),
        ):
            user_model = get_user_model()
            superuser, _ = user_model.objects.get_or_create(
                username="admin",
                defaults={
                    "first_name": "Admin",
                    "last_name": "User",
                    "email": "admin@care.test",
                    "is_superuser": True,
                    "is_staff": True,
                },
            )
            superuser.set_password("admin")
            superuser.is_superuser = True
            superuser.is_staff = True
            superuser.save()

            client = APIClient()
            client.force_authenticate(user=superuser)

            yield CareFixtureBase(client)
    finally:
        audit_logger.setLevel(original_level)
