
from django.db import migrations, models
from django.utils.timezone import now


def age_to_date_of_birth(apps, schema_editor):
    User = apps.get_model("users", "User")
    users_to_update = []
    for user in User.objects.all():
        if user.age:
            user.date_of_birth = now().replace(year=now().year - user.age)
            users_to_update.append(user)

    User.objects.bulk_update(users_to_update, ['date_of_birth'])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_alter_user_username"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),

        migrations.RunPython(age_to_date_of_birth, migrations.RunPython.noop),

        migrations.RemoveField(
            model_name="user",
            name="age",
        ),
    ]
