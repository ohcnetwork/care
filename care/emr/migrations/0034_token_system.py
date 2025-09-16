import django.contrib.postgres.fields
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def round_invoice_values(apps, schema_editor):
    Invoice = apps.get_model("emr", "Invoice")

    bulk = []
    for invoice in Invoice.objects.all().only("id", "total_net", "total_gross"):
        invoice.total_net = round(invoice.total_net, 2)
        invoice.total_gross = round(invoice.total_gross, 2)
        bulk.append(invoice)

    if bulk:
        Invoice.objects.bulk_update(bulk, ["total_net", "total_gross"])


class Migration(migrations.Migration):

    dependencies = [
        ('emr', '0033_healthcareservice_managing_organization'),
        ('facility', '0478_facility_discount_codes_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='requestor',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),

        migrations.RenameField(
            model_name='servicerequest',
            old_name='requestor',
            new_name='requester',
        ),

        migrations.AddField(
            model_name='schedulableuserresource',
            name='healthcare_service',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.healthcareservice'),
        ),
        migrations.AddField(
            model_name='schedulableuserresource',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.facilitylocation'),
        ),
        migrations.AddField(
            model_name='schedulableuserresource',
            name='resource_type',
            field=models.CharField(default='practitioner', max_length=255),
        ),
        migrations.AlterField(
            model_name='schedulableuserresource',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),

        migrations.RenameModel(
            old_name='SchedulableUserResource',
            new_name='SchedulableResource',
        ),

        migrations.CreateModel(
            name='TokenCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('resource_type', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('shorthand', models.CharField(max_length=255)),
                ('metadata', models.JSONField(default=dict)),
                ('default', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='facility.facility')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TokenQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('name', models.CharField(max_length=255)),
                ('is_primary', models.BooleanField(default=True)),
                ('date', models.DateField()),
                ('system_generated', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='facility.facility')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.schedulableresource')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TokenSubQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('name', models.CharField(max_length=255)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='facility.facility')),
                ('status', models.CharField(max_length=255)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.schedulableresource')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Token',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('number', models.IntegerField()),
                ('status', models.CharField(max_length=255)),
                ('is_next', models.BooleanField(default=False)),
                ('note', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='facility.facility')),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.patient')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.tokencategory')),
                ('queue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.tokenqueue')),
                ('sub_queue', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.tokensubqueue')),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='booking_token', to='emr.tokenbooking')),
            ],
            options={
                'abstract': False,
            },
        ),

        migrations.AddField(
            model_name='tokensubqueue',
            name='current_token',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.token'),
        ),

        migrations.CreateModel(
            name='ResourceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('resource_type', models.CharField(max_length=255)),
                ('title', models.CharField(max_length=255)),
                ('slug', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_child', models.BooleanField(default=False)),
                ('cached_parent_json', models.JSONField(default=dict)),
                ('parent_cache', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('level_cache', models.IntegerField(default=0)),
                ('has_children', models.BooleanField(default=False)),
                ('resource_sub_type', models.CharField(max_length=255)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='facility.facility')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='emr.resourcecategory')),
                ('root_org', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='root', to='emr.resourcecategory')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),

        migrations.AddIndex(
            model_name='resourcecategory',
            index=models.Index(fields=['slug', 'facility'], name='emr_resourc_slug_3dbacc_idx'),
        ),

        migrations.CreateModel(
            name='UserResourceFavorites',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('favorites', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('favorite_list', models.CharField(max_length=255)),
                ('resource_type', models.CharField(max_length=255)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='facility.facility')),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),

        migrations.CreateModel(
            name='MedicationRequestPrescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('modified_date', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('deleted', models.BooleanField(db_index=True, default=False)),
                ('history', models.JSONField(default=dict)),
                ('meta', models.JSONField(default=dict)),
                ('note', models.TextField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=100, null=True)),
                ('approval_status', models.CharField(blank=True, max_length=100, null=True)),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('alternate_identifier', models.CharField(blank=True, max_length=100, null=True)),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('created_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('encounter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.encounter')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='emr.patient')),
                ('prescribed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),

        migrations.AddConstraint(
            model_name='medicationrequestprescription',
            constraint=models.UniqueConstraint(fields=('alternate_identifier', 'encounter'), name='unique_alternate_identifier_encounter'),
        ),

        migrations.AddField(
            model_name='schedule',
            name='charge_item_definition',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='schedule_charge_item_definition', to='emr.chargeitemdefinition'),
        ),
        migrations.AddField(
            model_name='schedule',
            name='revisit_allowed_days',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schedule',
            name='revisit_charge_item_definition',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='schedule_revisit_charge_item_definition', to='emr.chargeitemdefinition'),
        ),

        migrations.AddField(
            model_name='tokenbooking',
            name='token',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='token_booking', to='emr.token'),
        ),
        migrations.AddField(
            model_name='tokenbooking',
            name='charge_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.chargeitem'),
        ),

        migrations.AddField(
            model_name='paymentreconciliation',
            name='is_credit_note',
            field=models.BooleanField(default=False),
        ),

        migrations.AddField(
            model_name='observationdefinition',
            name='qualified_ranges',
            field=models.JSONField(blank=True, default=list, null=True),
        ),

        migrations.AddField(
            model_name='medicationrequest',
            name='prescription',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='emr.medicationrequestprescription'),
        ),

        migrations.AddConstraint(
            model_name='schedulableresource',
            constraint=models.UniqueConstraint(fields=('facility', 'resource_type', 'user'), name='unique_facility_resource_user'),
        ),
        migrations.AddConstraint(
            model_name='schedulableresource',
            constraint=models.UniqueConstraint(fields=('facility', 'resource_type', 'location'), name='unique_facility_resource_location'),
        ),
        migrations.AddConstraint(
            model_name='schedulableresource',
            constraint=models.UniqueConstraint(fields=('facility', 'resource_type', 'healthcare_service'), name='unique_facility_resource_healthcare_service'),
        ),

        migrations.RenameField(
            model_name='activitydefinition',
            old_name='category',
            new_name='classification',
        ),

        migrations.AddField(
            model_name='activitydefinition',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.resourcecategory'),
        ),
        migrations.AddField(
            model_name='productknowledge',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.resourcecategory'),
        ),
        migrations.AddField(
            model_name='chargeitemdefinition',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.resourcecategory'),
        ),

        migrations.AlterField(
            model_name='chargeitem',
            name='encounter',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='emr.encounter'),
        ),

        migrations.RunPython(round_invoice_values, migrations.RunPython.noop),

        migrations.AlterField(
            model_name='invoice',
            name='total_gross',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total_net',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),

        migrations.RenameField(
            model_name='medicationdispense',
            old_name='authorizing_prescription',
            new_name='authorizing_request',
        ),
    ]
