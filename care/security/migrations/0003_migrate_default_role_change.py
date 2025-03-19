
from django.db import migrations, models

def update_default_role(apps, schema_editor):
    RoleModel = apps.get_model("security", "RoleModel")
    RoleModel.objects.filter(name="Geo Admin").update(name="Administrator")

class Migration(migrations.Migration):

    dependencies = [
        ('security', '0002_remove_rolemodel_unique_order_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=update_default_role,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
