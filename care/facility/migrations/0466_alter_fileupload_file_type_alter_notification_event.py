# Generated by Django 5.1.1 on 2024-10-01 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facility', '0465_merge_20240923_1045'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileupload',
            name='file_type',
            field=models.IntegerField(choices=[(0, 'OTHER'), (1, 'PATIENT'), (2, 'CONSULTATION'), (3, 'SAMPLE_MANAGEMENT'), (4, 'CLAIM'), (5, 'DISCHARGE_SUMMARY'), (6, 'COMMUNICATION'), (7, 'CONSENT_RECORD'), (8, 'ABDM_HEALTH_INFORMATION'), (9, 'NOTES')], default=1),
        ),
        migrations.AlterField(
            model_name='notification',
            name='event',
            field=models.IntegerField(choices=[(0, 'MESSAGE'), (20, 'PATIENT_CREATED'), (30, 'PATIENT_UPDATED'), (40, 'PATIENT_DELETED'), (50, 'PATIENT_CONSULTATION_CREATED'), (60, 'PATIENT_CONSULTATION_UPDATED'), (70, 'PATIENT_CONSULTATION_DELETED'), (80, 'INVESTIGATION_SESSION_CREATED'), (90, 'INVESTIGATION_UPDATED'), (100, 'PATIENT_FILE_UPLOAD_CREATED'), (110, 'CONSULTATION_FILE_UPLOAD_CREATED'), (120, 'PATIENT_CONSULTATION_UPDATE_CREATED'), (130, 'PATIENT_CONSULTATION_UPDATE_UPDATED'), (140, 'PATIENT_CONSULTATION_ASSIGNMENT'), (200, 'SHIFTING_UPDATED'), (210, 'PATIENT_NOTE_ADDED'), (220, 'PUSH_MESSAGE'), (230, 'PATIENT_PRESCRIPTION_CREATED'), (240, 'PATIENT_PRESCRIPTION_UPDATED'), (250, 'PATIENT_NOTE_MENTIONED')], default=0),
        ),
    ]
