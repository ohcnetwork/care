from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("facility", "0388_goal_goalentry_goalproperty_goalpropertyentry"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetlocation",
            name="duty_staff",
            field=models.ManyToManyField(
                blank=True,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
