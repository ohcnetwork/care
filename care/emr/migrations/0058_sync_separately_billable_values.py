from django.db import migrations


def sync_separately_billable(apps, schema_editor):
    ChargeItemDefinition = apps.get_model("emr", "ChargeItemDefinition")
    Product = apps.get_model("emr", "Product")
    Schedule = apps.get_model("emr", "Schedule")
    ActivityDefinition = apps.get_model("emr", "ActivityDefinition")

    for charge_item_def in ChargeItemDefinition.objects.all():
        is_linked = (
            Product.objects.filter(charge_item_definition_id=charge_item_def.id).exists()
            or Schedule.objects.filter(charge_item_definition_id=charge_item_def.id).exists()
            or Schedule.objects.filter(revisit_charge_item_definition_id=charge_item_def.id).exists()
            or ActivityDefinition.objects.filter(charge_item_definitions__contains=[charge_item_def.id]).exists()
        )

        if is_linked and charge_item_def.separately_billable:
            charge_item_def.separately_billable = False
            charge_item_def.save(update_fields=["separately_billable"])


class Migration(migrations.Migration):

    dependencies = [
        ("emr", "0057_add_separately_billable_to_charge_item_definition"),
    ]

    operations = [
        migrations.RunPython(sync_separately_billable),
    ]
