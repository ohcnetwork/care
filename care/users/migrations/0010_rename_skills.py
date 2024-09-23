# Generated by Django 4.2.5 on 2023-12-11 13:55

from django.db import migrations


def fix_skill_name(apps, schema_editor):
    Skill = apps.get_model("users", "Skill")

    fix = {
        "Anesthetists": "Anesthesiologist",
        "Emergency Medicine Physcian": "Emergency Medicine Physician",
        "Family Physcian": "Family Physician",
        "Intensivists": "Intensivist",
        "obstetrician and Gynecologists": "Obstetrician and Gynecologist",
        "Opthalmologists": "Ophthalmologist",
        "orthopaedic Surgeon": "Orthopedic Surgeon",
        "Orthopaedician": "Orthopedic",
        "Otolaryngologist ( ENT )": "Otolaryngologist (ENT)",
        "Palliative care Physcian": "Palliative care Physician",
        "Pathologists": "Pathologist",
        "Psychiatrists": "Psychiatrist",
        "Physcian": "Physician",
        "Pulmonologists": "Pulmonologist",
    }

    for old, new in fix.items():
        Skill.objects.filter(name=old).update(name=new)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0009_userfacilityallocation"),
    ]

    operations = [
        migrations.RunPython(fix_skill_name, migrations.RunPython.noop),
    ]
