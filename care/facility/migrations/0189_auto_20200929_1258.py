# Generated by Django 2.2.11 on 2020-09-29 07:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0188_auto_20200928_0139"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="date_of_result",
            field=models.DateTimeField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Patient's result Date",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="designation_of_health_care_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Designation of Health Care Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="frontline_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Front Line Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="instituion_of_health_care_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Institution of Healtcare Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="number_of_primary_contacts",
            field=models.IntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Number of Primary Contacts",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="number_of_secondary_contacts",
            field=models.IntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Number of Secondary Contacts",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="transit_details",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Transit Details (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientregistration",
            name="village",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Vilalge Name of Patient (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="date_of_result",
            field=models.DateTimeField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Patient's result Date",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="designation_of_health_care_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Designation of Health Care Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="frontline_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Front Line Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="instituion_of_health_care_worker",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Institution of Healtcare Worker (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="number_of_primary_contacts",
            field=models.IntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Number of Primary Contacts",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="number_of_secondary_contacts",
            field=models.IntegerField(
                blank=True,
                default=None,
                null=True,
                verbose_name="Number of Secondary Contacts",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="transit_details",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Transit Details (IDSP Req)",
            ),
        ),
        migrations.AddField(
            model_name="patientregistration",
            name="village",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Vilalge Name of Patient (IDSP Req)",
            ),
        ),
    ]
