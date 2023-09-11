from django.utils import timezone
from rest_framework.test import APITestCase

from care.facility.api.viewsets.patient import PatientFilterSet
from care.facility.models import Bed, ConsultationBed, PatientRegistration
from care.utils.tests.test_utils import TestUtils


class PatientFilterSetTestCase(TestUtils, APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(cls.district, cls.facility)
        cls.asset_location = cls.create_asset_location(cls.facility)

    def test_filter_by_bed_type(self):
        patient1 = self.create_patient(self.district, self.facility, name="patient1")
        patient2 = self.create_patient(self.district, self.facility, name="patient2")
        patient3 = self.patient

        # create beds
        bed1_data = {
            "name": "bed 1",
            "bed_type": 1,
            "location": self.asset_location,
            "facility": self.facility,
        }
        bed2_data = {
            "name": "bed 2",
            "bed_type": 2,
            "location": self.asset_location,
            "facility": self.facility,
        }

        bed1 = Bed.objects.create(**bed1_data)
        bed2 = Bed.objects.create(**bed2_data)

        consultation1 = self.create_consultation(
            patient=patient1, facility=self.facility
        )
        consultation2 = self.create_consultation(
            patient=patient2, facility=self.facility
        )
        consultation3 = self.create_consultation(
            patient=patient3, facility=self.facility
        )

        # consultation beds
        consultation_bed1 = ConsultationBed.objects.create(
            consultation=consultation1, bed=bed1, start_date=timezone.now()
        )
        consultation_bed2 = ConsultationBed.objects.create(
            consultation=consultation2, bed=bed2, start_date=timezone.now()
        )

        consultation1.current_bed = consultation_bed1
        consultation1.save(update_fields=["current_bed"])
        consultation2.current_bed = consultation_bed2
        consultation2.save(update_fields=["current_bed"])
        # None for consultation 3

        patient1.last_consultation = consultation1
        patient1.save(update_fields=["last_consultation"])
        patient2.last_consultation = consultation2
        patient2.save(update_fields=["last_consultation"])
        patient3.last_consultation = consultation3
        patient3.save(update_fields=["last_consultation"])

        # Create the filter set instance
        filterset = PatientFilterSet(queryset=PatientRegistration.objects.all())

        # filter
        filtered_queryset = filterset.filter_by_bed_type(
            name="last_consultation_admitted_bed_type_list",
            value="1,None",
            queryset=PatientRegistration.objects.all(),
        )
        self.assertEqual(len(filtered_queryset), 2)  # patient, patient1 and patient3
        self.assertTrue(patient1 in filtered_queryset)
        self.assertFalse(patient2 in filtered_queryset)
        self.assertTrue(patient3 in filtered_queryset)

        filtered_queryset = filterset.filter_by_bed_type(
            name="last_consultation_admitted_bed_type_list",
            value="None",
            queryset=PatientRegistration.objects.all(),
        )
        self.assertEqual(len(filtered_queryset), 1)
        self.assertFalse(patient1 in filtered_queryset)
        self.assertFalse(patient2 in filtered_queryset)
        self.assertTrue(patient3 in filtered_queryset)

        filtered_queryset = filterset.filter_by_bed_type(
            name="last_consultation_admitted_bed_type_list",
            value="2",
            queryset=PatientRegistration.objects.all(),
        )
        self.assertEqual(len(filtered_queryset), 1)
        self.assertFalse(patient1 in filtered_queryset)
        self.assertTrue(patient2 in filtered_queryset)
        self.assertFalse(patient3 in filtered_queryset)
