from django.test import TestCase
from django.utils import timezone

from care.facility.api.viewsets.patient import PatientFilterSet
from care.facility.models import (
    AssetLocation,
    Bed,
    ConsultationBed,
    Facility,
    PatientConsultation,
    PatientRegistration,
    State,
)
from care.facility.tests.mixins import TestClassMixin


class PatientFilterSetTestCase(TestClassMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.creator = self.users[0]
        state = State.objects.create(name="Kerala")

        # create patient registrations

        patient_data = {"gender": 1, "age": 30, "is_antenatal": False, "state": state}

        self.patient1 = PatientRegistration.objects.create(**patient_data)
        self.patient2 = PatientRegistration.objects.create(**patient_data)
        self.patient3 = PatientRegistration.objects.create(**patient_data)

        # Create Facility
        sample_data = {
            "name": "Hospital X",
            "ward": self.creator.ward,
            "local_body": self.creator.local_body,
            "district": self.creator.district,
            "state": self.creator.state,
            "facility_type": 1,
            "address": "Nearby",
            "pincode": 390024,
            "features": [],
        }
        self.facility = Facility.objects.create(
            external_id="550e8400-e29b-41d4-a716-446655440000",
            created_by=self.creator,
            **sample_data,
        )

        # create asset
        asset1 = AssetLocation.objects.create(
            name="asset1", location_type=1, facility=self.facility
        )

        # create beds
        bed1_data = {
            "name": "bed 1",
            "bed_type": 1,
            "location": asset1,
            "facility": self.facility,
        }
        bed2_data = {
            "name": "bed 2",
            "bed_type": 2,
            "location": asset1,
            "facility": self.facility,
        }

        bed1 = Bed.objects.create(**bed1_data)
        bed2 = Bed.objects.create(**bed2_data)

        # create consultations
        consultation1 = PatientConsultation.objects.create(
            patient=self.patient1,
            facility=self.facility,
        )
        consultation2 = PatientConsultation.objects.create(
            patient=self.patient2, facility=self.facility
        )
        consultation3 = PatientConsultation.objects.create(
            patient=self.patient3, facility=self.facility
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

        self.patient1.last_consultation = consultation1
        self.patient1.save(update_fields=["last_consultation"])
        self.patient2.last_consultation = consultation2
        self.patient2.save(update_fields=["last_consultation"])
        self.patient3.last_consultation = consultation3
        self.patient3.save(update_fields=["last_consultation"])

    def test_filter_by_bed_type(self):
        # Create the filter set instance with the desired queryset
        filterset = PatientFilterSet(queryset=PatientRegistration.objects.all())

        # Apply the filter manually
        filtered_queryset = filterset.filter_by_bed_type(
            name="last_consultation_admitted_bed_type_list",
            value="1,None",
            queryset=PatientRegistration.objects.all(),
        )

        # Assert the expected results
        self.assertEqual(len(filtered_queryset), 2)
        self.assertTrue(self.patient1 in filtered_queryset)
        self.assertFalse(self.patient2 in filtered_queryset)
        self.assertTrue(self.patient3 in filtered_queryset)
        self.assertEqual(filtered_queryset[0].last_consultation.current_bed, None)
        self.assertEqual(
            filtered_queryset[1].last_consultation.current_bed.bed.bed_type, 1
        )
