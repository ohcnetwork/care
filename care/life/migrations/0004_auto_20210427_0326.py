# Generated by Django 2.2.11 on 2021-04-26 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('life', '0003_auto_20210427_0129'),
    ]

    operations = [
        migrations.AddField(
            model_name='lifedata',
            name='created_on',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='lifedata',
            name='description',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='Verified_by',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='address',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='category',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='comment',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='created_by',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='email',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='last_verified_on',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='phone_1',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='phone_2',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='price',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='quantity_available',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='resource_type',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='source_link',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='lifedata',
            name='title',
            field=models.TextField(default=''),
        ),
    ]
