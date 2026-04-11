from decimal import Decimal

from django.db import models

from care.utils.models.base import BaseModel


class TenantPlanTier(models.TextChoices):
    LITE = "Lite", "Lite"
    PRO = "Pro", "Pro"


class BridgeSyncStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class Tenant(BaseModel):
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=63, unique=True)
    plan_tier = models.CharField(
        max_length=10,
        choices=TenantPlanTier.choices,
        default=TenantPlanTier.LITE,
    )
    is_active = models.BooleanField(default=True)
    abdm_bridge_id = models.CharField(max_length=255, blank=True, default="")
    logo_url = models.URLField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class MonthlyIncentive(BaseModel):
    tenant = models.ForeignKey(
        "parxio_core.Tenant",
        on_delete=models.CASCADE,
        related_name="monthly_incentives",
    )
    encounter = models.ForeignKey(
        "emr.Encounter",
        on_delete=models.CASCADE,
        related_name="monthly_incentives",
    )
    patient = models.ForeignKey(
        "emr.Patient",
        on_delete=models.CASCADE,
        related_name="monthly_incentives",
    )
    facility = models.ForeignKey(
        "facility.Facility",
        on_delete=models.CASCADE,
        related_name="monthly_incentives",
    )
    doctor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="monthly_incentives",
        null=True,
        blank=True,
    )
    prescription = models.ForeignKey(
        "emr.MedicationRequestPrescription",
        on_delete=models.SET_NULL,
        related_name="monthly_incentives",
        null=True,
        blank=True,
    )
    month = models.DateField()
    is_m2_compliant = models.BooleanField(default=False)
    parxio_cut = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("5.00")
    )
    doctor_cut = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("20.00")
    )
    bridge_status = models.CharField(
        max_length=20,
        choices=BridgeSyncStatus.choices,
        default=BridgeSyncStatus.PENDING,
    )
    bridge_reference = models.CharField(max_length=255, blank=True, default="")
    bridge_response = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "encounter", "month"],
                condition=models.Q(deleted=False),
                name="unique_tenant_monthly_incentive_encounter",
            )
        ]
