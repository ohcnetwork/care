from django.db import migrations, models
from django.utils.timezone import now


def age_to_date_of_birth(apps, schema_editor):
    User = apps.get_model("users", "User")
    users_to_update = []
    for user in User.objects.all():
        if user.age:
            user.date_of_birth = now().replace(year=now().year - user.age)
            users_to_update.append(user)

    User.objects.bulk_update(users_to_update, ["date_of_birth"])


def date_of_birth_to_age(apps, schema_editor):
    User = apps.get_model("users", "User")
    users_to_update = []
    for user in User.objects.all():
        if user.date_of_birth:
            user.age = (
                now().year
                - user.date_of_birth.year
                - (
                    (now().month, now().day)
                    < (user.date_of_birth.month, user.date_of_birth.day)
                )
            )
            users_to_update.append(user)

    User.objects.bulk_update(users_to_update, ["age"])


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
        migrations.RunPython(age_to_date_of_birth, date_of_birth_to_age),
        migrations.RemoveField(
            model_name="user",
            name="age",
        ),
    ]
