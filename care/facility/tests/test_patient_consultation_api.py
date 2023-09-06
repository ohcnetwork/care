import datetime
import random
from enum import Enum

from django.test import TestCase
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.api.viewsets.facility_users import FacilityUserViewSet
from care.facility.api.viewsets.patient_consultation import PatientConsultationViewSet
from care.facility.models import Bed, ConsultationBed
from care.facility.models.asset import Asset, AssetClasses, AssetLocation
from care.facility.models.facility import Facility
from care.facility.models.patient_consultation import (
    CATEGORY_CHOICES,
    PatientConsultation,
)
from care.facility.tests.mixins import TestClassMixin
from care.users.models import Skill, User
from care.utils.tests.test_base import TestBase


class ExpectedPatientConsultationListKeys(Enum):
    id = "id"
    is_kasp = "is_kasp"
    facility_name = "facility_name"
    is_telemedicine = "is_telemedicine"
    suggestion_text = "suggestion_text"
    kasp_enabled_date = "kasp_enabled_date"
    admitted = "admitted"
    admission_date = "admission_date"
    discharge_date = "discharge_date"
    created_date = "created_date"
    modified_date = "modified_date"
    last_edited_by = "last_edited_by"
    facility = "facility"
    patient = "patient"


class ExpectedLastEditedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class ExpectedPatientConsultationRetrieveKeys(Enum):
    id = "id"
    facility_name = "facility_name"
    facility = "facility"
    patient = "patient"
    last_edited_by = "last_edited_by"
    suggestion_text = "suggestion_text"
    symptoms = "symptoms"
    deprecated_covid_category = "deprecated_covid_category"
    category = "category"
    referred_to_object = "referred_to_object"
    referred_to = "referred_to"
    referred_to_external = "referred_to_external"
    assigned_to_object = "assigned_to_object"
    assigned_to = "assigned_to"
    discharge_reason = "discharge_reason"
    discharge_notes = "discharge_notes"
    discharge_prescription = "discharge_prescription"
    discharge_prn_prescription = "discharge_prn_prescription"
    review_interval = "review_interval"
    created_by = "created_by"
    last_daily_round = "last_daily_round"
    current_bed = "current_bed"
    icd11_diagnoses_object = "icd11_diagnoses_object"
    icd11_provisional_diagnoses_object = "icd11_provisional_diagnoses_object"
    created_date = "created_date"
    modified_date = "modified_date"
    diagnosis = "diagnosis"
    icd11_provisional_diagnoses = "icd11_provisional_diagnoses"
    icd11_diagnoses = "icd11_diagnoses"
    other_symptoms = "other_symptoms"
    symptoms_onset_date = "symptoms_onset_date"
    examination_details = "examination_details"
    history_of_present_illness = "history_of_present_illness"
    consultation_notes = "consultation_notes"
    course_in_facility = "course_in_facility"
    investigation = "investigation"
    prescriptions = "prescriptions"
    procedure = "procedure"
    suggestion = "suggestion"
    consultation_status = "consultation_status"
    admitted = "admitted"
    admission_date = "admission_date"
    discharge_date = "discharge_date"
    death_datetime = "death_datetime"
    death_confirmed_doctor = "death_confirmed_doctor"
    bed_number = "bed_number"
    is_kasp = "is_kasp"
    kasp_enabled_date = "kasp_enabled_date"
    is_telemedicine = "is_telemedicine"
    last_updated_by_telemedicine = "last_updated_by_telemedicine"
    verified_by = "verified_by"
    height = "height"
    weight = "weight"
    operation = "operation"
    special_instruction = "special_instruction"
    intubation_history = "intubation_history"
    prn_prescription = "prn_prescription"
    discharge_advice = "discharge_advice"
    patient_no = "patient_no"
    treatment_plan = "treatment_plan"


class ExpectedCreatedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class LocalBodyKeys(Enum):
    ID = "id"
    NAME = "name"
    BODY_TYPE = "body_type"
    LOCALBODY_CODE = "localbody_code"
    DISTRICT = "district"


class DistrictKeys(Enum):
    ID = "id"
    NAME = "name"
    STATE = "state"


class StateKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedReferredToKeys(Enum):
    ID = "id"
    NAME = "name"
    LOCAL_BODY = "local_body"
    DISTRICT = "district"
    STATE = "state"
    WARD_OBJECT = "ward_object"
    LOCAL_BODY_OBJECT = "local_body_object"
    DISTRICT_OBJECT = "district_object"
    STATE_OBJECT = "state_object"
    FACILITY_TYPE = "facility_type"
    READ_COVER_IMAGE_URL = "read_cover_image_url"
    FEATURES = "features"
    PATIENT_COUNT = "patient_count"
    BED_COUNT = "bed_count"


class WardKeys(Enum):
    ID = "id"
    NAME = "name"
    NUMBER = "number"
    LOCAL_BODY = "local_body"


class FacilityTypeKeys(Enum):
    ID = "id"
    NAME = "name"


class FacilityUserTest(TestClassMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.creator = self.users[0]

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

        self.skill1 = Skill.objects.create(name="Skill 1")
        self.skill2 = Skill.objects.create(name="Skill 2")

        self.users[0].skills.add(self.skill1, self.skill2)

    def test_get_queryset_with_prefetching(self):
        response = self.new_request(
            (f"/api/v1/facility/{self.facility.external_id}/get_users/",),
            {"get": "list"},
            FacilityUserViewSet,
            self.users[0],
            {"facility_external_id": self.facility.external_id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNumQueries(2)


class TestPatientConsultation(TestBase, TestClassMixin, APITestCase):
    default_data = {
        "symptoms": [1],
        "category": CATEGORY_CHOICES[0][0],
        "examination_details": "examination_details",
        "history_of_present_illness": "history_of_present_illness",
        "treatment_plan": "treatment_plan",
        "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][0],
    }

    def setUp(self):
        self.factory = APIRequestFactory()
        self.consultation = self.create_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
            referred_to=random.choices(Facility.objects.all())[0],
        )
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def create_admission_consultation(self, patient=None, **kwargs):
        patient = patient or self.create_patient(facility_id=self.facility.id)
        data = self.default_data.copy()
        kwargs.update(
            {
                "patient": patient.external_id,
                "facility": self.facility.external_id,
            }
        )
        data.update(kwargs)
        res = self.new_request(
            (self.get_url(), data, "json"),
            {"post": "create"},
            PatientConsultationViewSet,
            self.state_admin,
            {},
        )
        return PatientConsultation.objects.get(external_id=res.data["id"])

    def get_url(self, consultation=None):
        if consultation:
            return f"/api/v1/consultation/{consultation.external_id}"
        return "/api/v1/consultation"

    def discharge(self, consultation, **kwargs):
        return self.new_request(
            (f"{self.get_url(consultation)}/discharge_patient", kwargs, "json"),
            {"post": "discharge_patient"},
            PatientConsultationViewSet,
            self.state_admin,
            {"external_id": consultation.external_id},
        )

    def test_discharge_as_recovered_preadmission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2002-04-01T16:30:00Z",
            discharge_notes="Discharge as recovered before admission",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_future(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2319-04-01T15:30:00Z",
            discharge_notes="Discharge as recovered in the future",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_recovered_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2020-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered after admission before future",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_expired_pre_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2002-04-01T16:30:00Z",
            discharge_notes="Death before admission",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_future(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2319-04-01T15:30:00Z",
            discharge_notes="Death in the future",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_discharge_as_expired_after_admission(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="EXP",
            death_datetime="2020-04-02T15:30:00Z",
            discharge_notes="Death after admission before future",
            death_confirmed_doctor="Dr. Test",
            discharge_date="2319-04-01T15:30:00Z",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_discharge_as_recovered_with_expired_fields(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2023, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REC",
            discharge_date="2023-04-02T15:30:00Z",
            discharge_notes="Discharge as recovered with expired fields",
            death_datetime="2023-04-02T15:30:00Z",
            death_confirmed_doctor="Dr. Test",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        consultation.refresh_from_db()
        self.assertIsNone(consultation.death_datetime)
        self.assertIsNot(consultation.death_confirmed_doctor, "Dr. Test")

    def test_referred_to_external_null(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_empty_string(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to_external="",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_empty_facility(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with empty referred_to_external",
            referred_to=None,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_and_external_together(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with null referred_to_external",
            referred_to_external="External Facility",
            referred_to=self.facility.external_id,
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_referred_to_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_referred_to_external_valid_value(self):
        consultation = self.create_admission_consultation(
            suggestion="A",
            admission_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        referred_to_external = "Test Hospital"
        res = self.discharge(
            consultation,
            discharge_reason="REF",
            discharge_date="2023-07-01T12:00:00Z",
            discharge_notes="Discharged with valid referred_to_external",
            referred_to_external=referred_to_external,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_patient_consultation(self):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.super_user).access_token}"
        )
        response = client.get("/api/v1/consultation/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        district_lab_admin = self.create_user(
            district=self.district,
            username="district_lab_admin",
            user_type=User.TYPE_VALUE_MAP["DistrictLabAdmin"],
        )
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(district_lab_admin).access_token}"
        )
        response = client.get("/api/v1/consultation/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/api/v1/consultation/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedPatientConsultationListKeys]

        data = response.json()["results"][0]

        self.assertCountEqual(data.keys(), expected_keys)

        last_edited_by_keys = [key.value for key in ExpectedLastEditedByKeys]

        if data["last_edited_by"]:
            self.assertCountEqual(data["last_edited_by"].keys(), last_edited_by_keys)

    def test_retrieve_patient_consultation(self):
        response = self.client.get(
            f"/api/v1/consultation/{self.consultation.external_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedPatientConsultationRetrieveKeys]

        data = response.json()

        self.assertCountEqual(data.keys(), expected_keys)

        last_edited_by_keys = [key.value for key in ExpectedLastEditedByKeys]

        if data["last_edited_by"]:
            self.assertCountEqual(data["last_edited_by"].keys(), last_edited_by_keys)

        reffered_to_object_keys = [key.value for key in ExpectedReferredToKeys]
        self.assertCountEqual(
            data["referred_to_object"].keys(),
            reffered_to_object_keys,
        )

        ward_object_keys = [key.value for key in WardKeys]
        self.assertCountEqual(
            data["referred_to_object"]["ward_object"].keys(),
            ward_object_keys,
        )

        local_body_object_keys = [key.value for key in LocalBodyKeys]
        self.assertCountEqual(
            data["referred_to_object"]["local_body_object"].keys(),
            local_body_object_keys,
        )

        district_object_keys = [key.value for key in DistrictKeys]
        self.assertCountEqual(
            data["referred_to_object"]["district_object"].keys(),
            district_object_keys,
        )

        state_object_keys = [key.value for key in StateKeys]
        self.assertCountEqual(
            data["referred_to_object"]["state_object"].keys(),
            state_object_keys,
        )

        facility_object_keys = [key.value for key in FacilityTypeKeys]
        self.assertCountEqual(
            data["referred_to_object"]["facility_type"].keys(),
            facility_object_keys,
        )

    def test_generate_discharge_summary(self):
        url = f"/api/v1/consultation/{self.consultation.external_id}/generate_discharge_summary/"
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            res.data["detail"], "Discharge Summary will be generated shortly"
        )

    def test_patient_from_asset(self):
        asset1_location = AssetLocation.objects.create(
            name="asset1 location", location_type=1, facility=self.facility
        )
        asset = Asset.objects.create(
            name="Test Asset",
            current_location=asset1_location,
            asset_type=50,
            warranty_amc_end_of_validity=make_aware(
                datetime.datetime(2020, 4, 1, 15, 30, 00)
            ),
            asset_class=AssetClasses.ONVIF.name,
            meta={
                "asset_type": "CAMERA",
                "local_ip_address": "192.168.0.65",
                "camera_access_key": "remoteuser:aeAE55L5Po*S*C5:3af9acd0-2d4a-49e4-bb72-45cf7be0ae65",
                "middleware_hostname": "ka-kr-mysore.10bedicu.in",
            },
        )
        bed = Bed.objects.create(
            name="Fake Bed",
            description="This is a fake Bed",
            bed_type=5,
            facility=self.facility,
            location=asset1_location,
        )

        bed.assets.add(asset)
        self.user.asset = asset
        self.user.save()
        self.user.refresh_from_db()

        url = "/api/v1/consultation/patient_from_asset/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        consultation_bed = ConsultationBed.objects.create(
            consultation=self.consultation,
            bed=bed,
            start_date=make_aware(datetime.datetime(2020, 4, 1, 15, 30, 00)),
        )
        self.consultation.current_bed = consultation_bed
        self.consultation.save()
        self.consultation.refresh_from_db()
        consultation_bed.assets.add(asset)
        consultation_bed.refresh_from_db()

        url = "/api/v1/consultation/patient_from_asset/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_preview_discharge_summary(self):
        url = f"/api/v1/consultation/{self.consultation.external_id}/preview_discharge_summary/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            res.data["detail"], "Discharge Summary will be generated shortly"
        )
