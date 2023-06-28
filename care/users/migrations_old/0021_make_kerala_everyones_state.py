from django.db import migrations


def make_kerala_everyones_state(apps, *args):
    kerala = apps.get_model("users", "State").objects.get(name="Kerala")
    apps.get_model("users", "User").objects.all().update(state=kerala)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0020_auto_20200401_0930"),
    ]

    operations = [
        migrations.RunPython(make_kerala_everyones_state),
    ]
