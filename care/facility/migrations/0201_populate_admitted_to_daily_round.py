from django.db import migrations


def populate_admitted_to_daily_round(apps, *args):
    dailyround = apps.get_model("facility", "dailyround")
    for daily_round_obj in dailyround.objects.all():
        daily_round_obj.admitted_to = daily_round_obj.consultation.admitted_to
        daily_round_obj.save()


def reverse_populate_admitted_to_daily_round(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0200_dailyround_admitted_to"),
    ]

    operations = [
        migrations.RunPython(
            populate_admitted_to_daily_round,
            reverse_code=reverse_populate_admitted_to_daily_round,
        )
    ]
