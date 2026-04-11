from django.db import models

try:
    from django_multitenant.fields import TenantForeignKey as DjangoTenantForeignKey
except Exception:  # pragma: no cover
    DjangoTenantForeignKey = models.ForeignKey


TenantForeignKey = DjangoTenantForeignKey
