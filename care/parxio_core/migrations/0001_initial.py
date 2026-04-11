import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("facility", "0484_remove_facility_discount_codes_and_more"),
        ("emr", "0074_facilitymonetoryconfig"),
        ("users", "0027_user_cached_role_orgs"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("created_date", models.DateTimeField(auto_now_add=True, blank=True, db_index=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, blank=True, db_index=True, null=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                ("name", models.CharField(max_length=255)),
                ("subdomain", models.CharField(max_length=63, unique=True)),
                ("plan_tier", models.CharField(choices=[("Lite", "Lite"), ("Pro", "Pro")], default="Lite", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("abdm_bridge_id", models.CharField(blank=True, default="", max_length=255)),
                ("logo_url", models.URLField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="MonthlyIncentive",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("created_date", models.DateTimeField(auto_now_add=True, blank=True, db_index=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, blank=True, db_index=True, null=True)),
                ("deleted", models.BooleanField(db_index=True, default=False)),
                ("month", models.DateField()),
                ("is_m2_compliant", models.BooleanField(default=False)),
                ("parxio_cut", models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=10)),
                ("doctor_cut", models.DecimalField(decimal_places=2, default=Decimal("20.00"), max_digits=10)),
                ("bridge_status", models.CharField(choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed"), ("skipped", "Skipped")], default="pending", max_length=20)),
                ("bridge_reference", models.CharField(blank=True, default="", max_length=255)),
                ("bridge_response", models.JSONField(blank=True, default=dict)),
                ("doctor", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="monthly_incentives", to="users.user")),
                ("encounter", models.ForeignKey(on_delete=models.CASCADE, related_name="monthly_incentives", to="emr.encounter")),
                ("facility", models.ForeignKey(on_delete=models.CASCADE, related_name="monthly_incentives", to="facility.facility")),
                ("patient", models.ForeignKey(on_delete=models.CASCADE, related_name="monthly_incentives", to="emr.patient")),
                ("prescription", models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="monthly_incentives", to="emr.medicationrequestprescription")),
                ("tenant", models.ForeignKey(on_delete=models.CASCADE, related_name="monthly_incentives", to="parxio_core.tenant")),
            ],
            options={},
        ),
        migrations.AddConstraint(
            model_name="monthlyincentive",
            constraint=models.UniqueConstraint(condition=models.Q(("deleted", False)), fields=("tenant", "encounter", "month"), name="unique_tenant_monthly_incentive_encounter"),
        ),
    ]
