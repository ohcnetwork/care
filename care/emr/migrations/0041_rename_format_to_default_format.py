# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emr', '0040_template_reportupload'),
    ]

    operations = [
        migrations.RenameField(
            model_name='template',
            old_name='format',
            new_name='default_format',
        ),
    ]
