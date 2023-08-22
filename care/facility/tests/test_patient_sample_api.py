from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedPatientSampleListKeys(Enum):
    id = "id"
    status = "status"
    sample_type = "sample_type"
    result = "result"
    date_of_sample = "date_of_sample"
    date_of_result = "date_of_result"
    created_date = "created_date"
    created_by = "created_by"
    last_edited_by = "last_edited_by"
    modified_date = "modified_date"
    sample_type_other = "sample_type_other"
    fast_track = "fast_track"


class ExpectedPatientSampleRetrieveKeys(Enum):
    id = "id"
    patient_object = "patient_object"
    patient_name = "patient_name"
    patient_has_sari = "patient_has_sari"
    patient_has_confirmed_contact = "patient_has_confirmed_contact"
    patient_has_suspected_contact = "patient_has_suspected_contact"
    patient_travel_history = "patient_travel_history"
    facility = "facility"
    facility_object = "facility_object"
    sample_type = "sample_type"
    status = "status"
    result = "result"
    icmr_category = "icmr_category"
    patient = "patient"
    consultation = "consultation"
    date_of_sample = "date_of_sample"
    date_of_result = "date_of_result"
    testing_facility = "testing_facility"
    testing_facility_object = "testing_facility_object"
    last_edited_by = "last_edited_by"
    created_by = "created_by"
    flow = "flow"
    created_date = "created_date"
    modified_date = "modified_date"
    sample_type_other = "sample_type_other"
    has_sari = "has_sari"
    has_ari = "has_ari"
    doctor_name = "doctor_name"
    diagnosis = "diagnosis"
    diff_diagnosis = "diff_diagnosis"
    etiology_identified = "etiology_identified"
    is_atypical_presentation = "is_atypical_presentation"
    atypical_presentation = "atypical_presentation"
    is_unusual_course = "is_unusual_course"
    icmr_label = "icmr_label"
    fast_track = "fast_track"


class ExpectedConsultationKeys(Enum):
    ID = "id"
    FACILITY_NAME = "facility_name"
    SUGGESTION_TEXT = "suggestion_text"
    SYMPTOMS = "symptoms"
    DEPRECATED_COVID_CATEGORY = "deprecated_covid_category"
    CATEGORY = "category"
    REFERRED_TO_OBJECT = "referred_to_object"
    REFERRED_TO = "referred_to"
    REFERRED_TO_EXTERNAL = "referred_to_external"
    PATIENT = "patient"
    FACILITY = "facility"
    ASSIGNED_TO_OBJECT = "assigned_to_object"
    ASSIGNED_TO = "assigned_to"
    DISCHARGE_REASON = "discharge_reason"
    DISCHARGE_NOTES = "discharge_notes"
    DISCHARGE_PRESCRIPTION = "discharge_prescription"
    DISCHARGE_PRN_PRESCRIPTION = "discharge_prn_prescription"
    REVIEW_INTERVAL = "review_interval"
    LAST_EDITED_BY = "last_edited_by"
    LAST_DAILY_ROUND = "last_daily_round"
    CURRENT_BED = "current_bed"
    ICD11_DIAGNOSES_OBJECT = "icd11_diagnoses_object"
    ICD11_PROVISIONAL_DIAGNOSES_OBJECT = "icd11_provisional_diagnoses_object"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    IP_NO = "ip_no"
    OP_NO = "op_no"
    DIAGNOSIS = "diagnosis"
    ICD11_PROVISIONAL_DIAGNOSES = "icd11_provisional_diagnoses"
    ICD11_DIAGNOSES = "icd11_diagnoses"
    OTHER_SYMPTOMS = "other_symptoms"
    SYMPTOMS_ONSET_DATE = "symptoms_onset_date"
    EXAMINATION_DETAILS = "examination_details"
    HISTORY_OF_PRESENT_ILLNESS = "history_of_present_illness"
    PRESCRIBED_MEDICATION = "prescribed_medication"
    CONSULTATION_NOTES = "consultation_notes"
    COURSE_IN_FACILITY = "course_in_facility"
    INVESTIGATION = "investigation"
    PRESCRIPTIONS = "prescriptions"
    PROCEDURE = "procedure"
    SUGGESTION = "suggestion"
    CONSULTATION_STATUS = "consultation_status"
    ADMITTED = "admitted"
    ADMISSION_DATE = "admission_date"
    DISCHARGE_DATE = "discharge_date"
    DEATH_DATETIME = "death_datetime"
    DEATH_CONFIRMED_DOCTOR = "death_confirmed_doctor"
    BED_NUMBER = "bed_number"
    IS_KASP = "is_kasp"
    KASP_ENABLED_DATE = "kasp_enabled_date"
    IS_TELEMEDICINE = "is_telemedicine"
    LAST_UPDATED_BY_TELEMEDICINE = "last_updated_by_telemedicine"
    VERIFIED_BY = "verified_by"
    HEIGHT = "height"
    WEIGHT = "weight"
    OPERATION = "operation"
    SPECIAL_INSTRUCTION = "special_instruction"
    INTUBATION_HISTORY = "intubation_history"
    PRN_PRESCRIPTION = "prn_prescription"
    DISCHARGE_ADVICE = "discharge_advice"
    CREATED_BY = "created_by"


class ExpectedPatientObjectKeys(Enum):
    id = "id"
    facility = "facility"
    facility_object = "facility_object"
    ward_object = "ward_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    state_object = "state_object"
    last_consultation = "last_consultation"
    blood_group = "blood_group"
    disease_status = "disease_status"
    source = "source"
    assigned_to_object = "assigned_to_object"
    has_eligible_policy = "has_eligible_policy"
    approved_claim_amount = "approved_claim_amount"
    medical_history = "medical_history"
    tele_consultation_history = "tele_consultation_history"
    meta_info = "meta_info"
    contacted_patients = "contacted_patients"
    test_type = "test_type"
    last_edited = "last_edited"
    created_by = "created_by"
    vaccine_name = "vaccine_name"
    assigned_to = "assigned_to"
    allow_transfer = "allow_transfer"
    abha_number = "abha_number"
    abha_number_object = "abha_number_object"
    created_date = "created_date"
    modified_date = "modified_date"
    name = "name"
    age = "age"
    gender = "gender"
    phone_number = "phone_number"
    emergency_phone_number = "emergency_phone_number"
    address = "address"
    permanent_address = "permanent_address"
    pincode = "pincode"
    date_of_birth = "date_of_birth"
    nationality = "nationality"
    passport_no = "passport_no"
    is_medical_worker = "is_medical_worker"
    contact_with_confirmed_carrier = "contact_with_confirmed_carrier"
    contact_with_suspected_carrier = "contact_with_suspected_carrier"
    estimated_contact_date = "estimated_contact_date"
    past_travel = "past_travel"
    countries_travelled = "countries_travelled"
    date_of_return = "date_of_return"
    allergies = "allergies"
    present_health = "present_health"
    ongoing_medication = "ongoing_medication"
    has_SARI = "has_SARI"
    is_antenatal = "is_antenatal"
    ward_old = "ward_old"
    is_migrant_worker = "is_migrant_worker"
    number_of_aged_dependents = "number_of_aged_dependents"
    number_of_chronic_diseased_dependents = "number_of_chronic_diseased_dependents"
    action = "action"
    review_time = "review_time"
    is_active = "is_active"
    date_of_receipt_of_information = "date_of_receipt_of_information"
    test_id = "test_id"
    date_of_test = "date_of_test"
    srf_id = "srf_id"
    will_donate_blood = "will_donate_blood"
    fit_for_blood_donation = "fit_for_blood_donation"
    village = "village"
    designation_of_health_care_worker = "designation_of_health_care_worker"
    instituion_of_health_care_worker = "instituion_of_health_care_worker"
    transit_details = "transit_details"
    frontline_worker = "frontline_worker"
    date_of_result = "date_of_result"
    number_of_primary_contacts = "number_of_primary_contacts"
    number_of_secondary_contacts = "number_of_secondary_contacts"
    is_vaccinated = "is_vaccinated"
    number_of_doses = "number_of_doses"
    covin_id = "covin_id"
    last_vaccinated_date = "last_vaccinated_date"
    cluster_name = "cluster_name"
    is_declared_positive = "is_declared_positive"
    date_declared_positive = "date_declared_positive"
    nearest_facility = "nearest_facility"
    ward = "ward"
    local_body = "local_body"
    district = "district"
    state = "state"


class ExpectedFacilityKeys(Enum):
    ID = "id"
    NAME = "name"
    WARD = "ward"
    LOCAL_BODY = "local_body"
    DISTRICT = "district"
    STATE = "state"
    FACILITY_TYPE = "facility_type"
    ADDRESS = "address"
    LONGITUDE = "longitude"
    LATITUDE = "latitude"
    FEATURES = "features"
    PINCODE = "pincode"
    OXYGEN_CAPACITY = "oxygen_capacity"
    PHONE_NUMBER = "phone_number"
    WARD_OBJECT = "ward_object"
    LOCAL_BODY_OBJECT = "local_body_object"
    DISTRICT_OBJECT = "district_object"
    STATE_OBJECT = "state_object"
    MODIFIED_DATE = "modified_date"
    CREATED_DATE = "created_date"
    KASP_EMPANELLED = "kasp_empanelled"
    MIDDLEWARE_ADDRESS = "middleware_address"
    EXPECTED_OXYGEN_REQUIREMENT = "expected_oxygen_requirement"
    TYPE_B_CYLINDERS = "type_b_cylinders"
    TYPE_C_CYLINDERS = "type_c_cylinders"
    TYPE_D_CYLINDERS = "type_d_cylinders"
    EXPECTED_TYPE_B_CYLINDERS = "expected_type_b_cylinders"
    EXPECTED_TYPE_C_CYLINDERS = "expected_type_c_cylinders"
    EXPECTED_TYPE_D_CYLINDERS = "expected_type_d_cylinders"
    READ_COVER_IMAGE_URL = "read_cover_image_url"
    PATIENT_COUNT = "patient_count"
    BED_COUNT = "bed_count"


class ExpectedMedicalHistoryDetailsKeys(Enum):
    disease = "disease"
    details = "details"


class ExpectedCreatedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class ExpectedLastEditedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class ExpectedFacilityObjectKeys(Enum):
    id = "id"
    name = "name"
    local_body = "local_body"
    district = "district"
    state = "state"
    ward_object = "ward_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    state_object = "state_object"
    facility_type = "facility_type"
    read_cover_image_url = "read_cover_image_url"
    features = "features"
    patient_count = "patient_count"
    bed_count = "bed_count"


class ExpectedTestingFacilityObjectKeys(Enum):
    id = "id"
    name = "name"
    local_body = "local_body"
    district = "district"
    state = "state"
    ward_object = "ward_object"
    local_body_object = "local_body_object"
    district_object = "district_object"
    state_object = "state_object"
    facility_type = "facility_type"
    read_cover_image_url = "read_cover_image_url"
    features = "features"
    patient_count = "patient_count"
    bed_count = "bed_count"


class WardKeys(Enum):
    ID = "id"
    NAME = "name"
    NUMBER = "number"
    LOCAL_BODY = "local_body"


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


class PatientSampleViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        cls.patient_sample_test = cls.create_patient_sample()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_patient_sample(self):
        print(self.patient_sample_test.external_id)
        response = self.client.get(
            f"/api/v1/patient/{self.patient.external_id}/test_sample/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedPatientSampleListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

    def test_retrieve_patient_sample(self):
        response = self.client.get(
            f"/api/v1/patient/{self.patient.external_id}/test_sample/{self.patient_sample_test.external_id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedPatientSampleRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        expected_patient_keys = [key.value for key in ExpectedPatientObjectKeys]
        patient_data = data["patient_object"]
        self.assertCountEqual(patient_data.keys(), expected_patient_keys)

        expected_facility_keys = [key.value for key in ExpectedFacilityKeys]
        facility_data = data["patient_object"]["facility_object"]
        self.assertCountEqual(facility_data.keys(), expected_facility_keys)

        expected_ward_keys = [key.value for key in WardKeys]
        ward_data = data["patient_object"]["ward_object"]
        if ward_data:
            self.assertCountEqual(ward_data.keys(), expected_ward_keys)

        expected_local_body_keys = [key.value for key in LocalBodyKeys]
        local_body_data = data["patient_object"]["local_body_object"]
        if local_body_data:
            self.assertCountEqual(local_body_data.keys(), expected_local_body_keys)

        expected_district_keys = [key.value for key in DistrictKeys]
        district_data = data["patient_object"]["district_object"]
        if district_data:
            self.assertCountEqual(district_data.keys(), expected_district_keys)

        expected_state_keys = [key.value for key in StateKeys]
        state_data = data["patient_object"]["state_object"]
        if state_data:
            self.assertCountEqual(state_data.keys(), expected_state_keys)

        expected_last_consultation = [key.value for key in ExpectedConsultationKeys]
        last_consultation_data = data["patient_object"]["last_consultation"]
        if last_consultation_data:
            self.assertCountEqual(
                last_consultation_data.keys(), expected_last_consultation
            )

        expected_medical_history = [
            key.value for key in ExpectedMedicalHistoryDetailsKeys
        ]
        medical_history_data = data["patient_object"]["medical_history"]
        if medical_history_data:
            self.assertCountEqual(
                medical_history_data[0].keys(), expected_medical_history
            )

        expected_last_edited_by_keys = [key.value for key in ExpectedLastEditedByKeys]
        if "last_edited_by" in data["patient_object"]:
            last_edited_by_data = data["patient_object"]["last_edited_by"]
            if last_edited_by_data:
                self.assertCountEqual(
                    last_edited_by_data.keys(), expected_last_edited_by_keys
                )

        expected_created_by_keys = [key.value for key in ExpectedCreatedByKeys]
        created_by_data = data["patient_object"]["created_by"]
        if created_by_data:
            self.assertCountEqual(created_by_data.keys(), expected_created_by_keys)

        expected_facility_object_keys = [
            key.value for key in ExpectedFacilityObjectKeys
        ]
        facility_object_data = data["facility_object"]
        self.assertCountEqual(
            facility_object_data.keys(), expected_facility_object_keys
        )

        if "last_edited_by" in data:
            last_edited_by_data = data["last_edited_by"]
            if last_edited_by_data:
                self.assertCountEqual(
                    last_edited_by_data.keys(), expected_last_edited_by_keys
                )

        if "created_by" in data:
            created_by_data = data["created_by"]
            if created_by_data:
                self.assertCountEqual(created_by_data.keys(), expected_created_by_keys)
