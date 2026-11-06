from django.db import migrations, models
from django.db.models import Exists, OuterRef


def backfill_child_flags(apps, schema_editor):
    location = apps.get_model("emr", "FacilityLocation")
    locations = location.objects.using(schema_editor.connection.alias)
    children = locations.filter(parent_id=OuterRef("pk"), deleted=False)
    locations.update(
        has_children=Exists(children),
        has_sub_locations=Exists(children.filter(mode="kind")),
        has_beds=Exists(children.filter(mode="instance")),
        cached_parent_json={},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("emr", "0100_merge_20261025_0238"),
    ]

    operations = [
        migrations.AddField(
            model_name="facilitylocation",
            name="has_sub_locations",
            field=models.BooleanField(
                default=False,
                help_text="Whether this location has direct, undeleted child locations in kind mode.",
            ),
        ),
        migrations.AddField(
            model_name="facilitylocation",
            name="has_beds",
            field=models.BooleanField(
                default=False,
                help_text="Whether this location has direct, undeleted child locations in instance mode.",
            ),
        ),
        migrations.RunPython(backfill_child_flags, migrations.RunPython.noop),
    ]
