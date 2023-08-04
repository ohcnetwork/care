from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.tests.mixins import TestClassMixin
from care.utils.tests.test_base import TestBase


class ExpectedPolicyListKeys(Enum):
    ID = "id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    SUBSCRIBER_ID = "subscriber_id"
    POLICY_ID = "policy_id"
    INSURER_ID = "insurer_id"
    INSURER_NAME = "insurer_name"


class ExpectedItemKeys(Enum):
    ID = "id"
    NAME = "name"
    PRICE = "price"
    CATEGORY = "category"


class ExpectedClaimListKeys(Enum):
    ID = "id"
    OUTCOME = "outcome"
    ERROR_TEXT = "error_text"
    CREATED_DATE = "created_date"
    USE = "use"
    POLICY_OBJECT = "policy_object"
    ITEMS = "items"
    TOTAL_CLAIM_AMOUNT = "total_claim_amount"
    MODIFIED_DATE = "modified_date"


class ExpectedClaimRetrieveKeys(Enum):
    ID = "id"
    CONSULTATION_OBJECT = "consultation_object"
    POLICY_OBJECT = "policy_object"
    ITEMS = "items"
    TOTAL_CLAIM_AMOUNT = "total_claim_amount"
    TOTAL_AMOUNT_APPROVED = "total_amount_approved"
    USE = "use"
    STATUS = "status"
    PRIORITY = "priority"
    TYPE = "type"
    OUTCOME = "outcome"
    ERROR_TEXT = "error_text"
    CREATED_BY = "created_by"
    LAST_MODIFIED_BY = "last_modified_by"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"


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


class ExpectedPolicyRetrieveKeys(Enum):
    ID = "id"
    PATIENT_OBJECT = "patient_object"
    SUBSCRIBER_ID = "subscriber_id"
    POLICY_ID = "policy_id"
    INSURER_ID = "insurer_id"
    INSURER_NAME = "insurer_name"
    STATUS = "status"
    PRIORITY = "priority"
    PURPOSE = "purpose"
    OUTCOME = "outcome"
    ERROR_TEXT = "error_text"
    CREATED_BY = "created_by"
    LAST_MODIFIED_BY = "last_modified_by"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"


class ExpectedDailyRoundRetrieveData(Enum):
    ID = "id"
    PATIENT_CATEGORY = "patient_category"
    LAST_EDITED_BY = "last_edited_by"
    CREATED_BY = "created_by"
    ADDITIONAL_SYMPTOMS = "additional_symptoms"
    DEPRECATED_COVID_CATEGORY = "deprecated_covid_category"
    CURRENT_HEALTH = "current_health"
    TAKEN_AT = "taken_at"
    ROUNDS_TYPE = "rounds_type"
    CONSCIOUSNESS_LEVEL = "consciousness_level"
    LEFT_PUPIL_LIGHT_REACTION = "left_pupil_light_reaction"
    RIGHT_PUPIL_LIGHT_REACTION = "right_pupil_light_reaction"
    LIMB_RESPONSE_UPPER_EXTREMITY_RIGHT = "limb_response_upper_extremity_right"
    LIMB_RESPONSE_UPPER_EXTREMITY_LEFT = "limb_response_upper_extremity_left"
    LIMB_RESPONSE_LOWER_EXTREMITY_LEFT = "limb_response_lower_extremity_left"
    LIMB_RESPONSE_LOWER_EXTREMITY_RIGHT = "limb_response_lower_extremity_right"
    RHYTHM = "rhythm"
    VENTILATOR_INTERFACE = "ventilator_interface"
    VENTILATOR_MODE = "ventilator_mode"
    VENTILATOR_OXYGEN_MODALITY = "ventilator_oxygen_modality"
    INSULIN_INTAKE_FREQUENCY = "insulin_intake_frequency"
    EXTERNAL_ID = "external_id"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    TEMPERATURE = "temperature"
    SPO2 = "spo2"
    TEMPERATURE_MEASURED_AT = "temperature_measured_at"
    PHYSICAL_EXAMINATION_INFO = "physical_examination_info"
    OTHER_SYMPTOMS = "other_symptoms"
    RECOMMEND_DISCHARGE = "recommend_discharge"
    OTHER_DETAILS = "other_details"
    MEDICATION_GIVEN = "medication_given"
    LAST_UPDATED_BY_TELEMEDICINE = "last_updated_by_telemedicine"
    CREATED_BY_TELEMEDICINE = "created_by_telemedicine"
    CONSCIOUSNESS_LEVEL_DETAIL = "consciousness_level_detail"
    IN_PRONE_POSITION = "in_prone_position"
    LEFT_PUPIL_SIZE = "left_pupil_size"
    LEFT_PUPIL_SIZE_DETAIL = "left_pupil_size_detail"
    LEFT_PUPIL_LIGHT_REACTION_DETAIL = "left_pupil_light_reaction_detail"
    RIGHT_PUPIL_SIZE = "right_pupil_size"
    RIGHT_PUPIL_SIZE_DETAIL = "right_pupil_size_detail"
    RIGHT_PUPIL_LIGHT_REACTION_DETAIL = "right_pupil_light_reaction_detail"
    GLASGOW_EYE_OPEN = "glasgow_eye_open"
    GLASGOW_VERBAL_RESPONSE = "glasgow_verbal_response"
    GLASGOW_MOTOR_RESPONSE = "glasgow_motor_response"
    GLASGOW_TOTAL_CALCULATED = "glasgow_total_calculated"
    BP = "bp"
    PULSE = "pulse"
    RESP = "resp"
    RHYTHM_DETAIL = "rhythm_detail"
    VENTILATOR_PEEP = "ventilator_peep"
    VENTILATOR_PIP = "ventilator_pip"
    VENTILATOR_MEAN_AIRWAY_PRESSURE = "ventilator_mean_airway_pressure"
    VENTILATOR_RESP_RATE = "ventilator_resp_rate"
    VENTILATOR_PRESSURE_SUPPORT = "ventilator_pressure_support"
    VENTILATOR_TIDAL_VOLUME = "ventilator_tidal_volume"
    VENTILATOR_OXYGEN_MODALITY_OXYGEN_RATE = "ventilator_oxygen_modality_oxygen_rate"
    VENTILATOR_OXYGEN_MODALITY_FLOW_RATE = "ventilator_oxygen_modality_flow_rate"
    VENTILATOR_FI02 = "ventilator_fi02"
    VENTILATOR_SPO2 = "ventilator_spo2"
    ETCO2 = "etco2"
    BILATERAL_AIR_ENTRY = "bilateral_air_entry"
    PAIN = "pain"
    PAIN_SCALE_ENHANCED = "pain_scale_enhanced"
    PH = "ph"
    PCO2 = "pco2"
    PO2 = "po2"
    HCO3 = "hco3"
    BASE_EXCESS = "base_excess"
    LACTATE = "lactate"
    SODIUM = "sodium"
    POTASSIUM = "potassium"
    BLOOD_SUGAR_LEVEL = "blood_sugar_level"
    INSULIN_INTAKE_DOSE = "insulin_intake_dose"
    INFUSIONS = "infusions"
    IV_FLUIDS = "iv_fluids"
    FEEDS = "feeds"
    TOTAL_INTAKE_CALCULATED = "total_intake_calculated"
    OUTPUT = "output"
    TOTAL_OUTPUT_CALCULATED = "total_output_calculated"
    DIALYSIS_FLUID_BALANCE = "dialysis_fluid_balance"
    DIALYSIS_NET_BALANCE = "dialysis_net_balance"
    PRESSURE_SORE = "pressure_sore"
    NURSING = "nursing"
    MEDICINE_ADMINISTRATION = "medicine_administration"
    META = "meta"
    CONSULTATION = "consultation"


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


class LastConsultation(Enum):
    ID = "id"
    FACILITY_NAME = "facility_name"
    SUGGESTION_TEXT = "suggestion_text"
    SYMPTOMS = "symptoms"


class FacilityTypeKeys(Enum):
    ID = "id"
    NAME = "name"


class ExpectedPatientObjectKeys(Enum):
    ID = "id"
    FACILITY = "facility"
    FACILITY_OBJECT = "facility_object"
    WARD_OBJECT = "ward_object"
    LOCAL_BODY_OBJECT = "local_body_object"
    DISTRICT_OBJECT = "district_object"
    STATE_OBJECT = "state_object"
    LAST_CONSULTATION = "last_consultation"
    BLOOD_GROUP = "blood_group"
    DISEASE_STATUS = "disease_status"
    SOURCE = "source"
    ASSIGNED_TO_OBJECT = "assigned_to_object"
    HAS_ELIGIBLE_POLICY = "has_eligible_policy"
    APPROVED_CLAIM_AMOUNT = "approved_claim_amount"
    MEDICAL_HISTORY = "medical_history"
    TELE_CONSULTATION_HISTORY = "tele_consultation_history"
    META_INFO = "meta_info"
    CONTACTED_PATIENTS = "contacted_patients"
    TEST_TYPE = "test_type"
    LAST_EDITED = "last_edited"
    CREATED_BY = "created_by"
    VACCINE_NAME = "vaccine_name"
    ASSIGNED_TO = "assigned_to"
    ALLOW_TRANSFER = "allow_transfer"
    ABHA_NUMBER = "abha_number"
    ABHA_NUMBER_OBJECT = "abha_number_object"
    CREATED_DATE = "created_date"
    MODIFIED_DATE = "modified_date"
    NAME = "name"
    AGE = "age"
    GENDER = "gender"
    PHONE_NUMBER = "phone_number"
    EMERGENCY_PHONE_NUMBER = "emergency_phone_number"
    ADDRESS = "address"
    PERMANENT_ADDRESS = "permanent_address"
    PINCODE = "pincode"
    DATE_OF_BIRTH = "date_of_birth"
    NATIONALITY = "nationality"
    PASSPORT_NO = "passport_no"
    IS_MEDICAL_WORKER = "is_medical_worker"
    CONTACT_WITH_CONFIRMED_CARRIER = "contact_with_confirmed_carrier"
    CONTACT_WITH_SUSPECTED_CARRIER = "contact_with_suspected_carrier"
    ESTIMATED_CONTACT_DATE = "estimated_contact_date"
    PAST_TRAVEL = "past_travel"
    COUNTRIES_TRAVELLED = "countries_travelled"
    DATE_OF_RETURN = "date_of_return"
    ALLERGIES = "allergies"
    PRESENT_HEALTH = "present_health"
    ONGOING_MEDICATION = "ongoing_medication"
    HAS_SARI = "has_SARI"
    IS_ANTENATAL = "is_antenatal"
    WARD_OLD = "ward_old"
    IS_MIGRANT_WORKER = "is_migrant_worker"
    NUMBER_OF_AGED_DEPENDENTS = "number_of_aged_dependents"
    NUMBER_OF_CHRONIC_DISEASED_DEPENDENTS = "number_of_chronic_diseased_dependents"
    ACTION = "action"
    REVIEW_TIME = "review_time"
    IS_ACTIVE = "is_active"
    DATE_OF_RECEIPT_OF_INFORMATION = "date_of_receipt_of_information"
    TEST_ID = "test_id"
    DATE_OF_TEST = "date_of_test"
    SRF_ID = "srf_id"
    WILL_DONATE_BLOOD = "will_donate_blood"
    FIT_FOR_BLOOD_DONATION = "fit_for_blood_donation"
    VILLAGE = "village"
    DESIGNATION_OF_HEALTH_CARE_WORKER = "designation_of_health_care_worker"
    INSTITUION_OF_HEALTH_CARE_WORKER = "instituion_of_health_care_worker"
    TRANSIT_DETAILS = "transit_details"
    FRONTLINE_WORKER = "frontline_worker"
    DATE_OF_RESULT = "date_of_result"
    NUMBER_OF_PRIMARY_CONTACTS = "number_of_primary_contacts"
    NUMBER_OF_SECONDARY_CONTACTS = "number_of_secondary_contacts"
    IS_VACCINATED = "is_vaccinated"
    NUMBER_OF_DOSES = "number_of_doses"
    COVIN_ID = "covin_id"
    LAST_VACCINATED_DATE = "last_vaccinated_date"
    CLUSTER_NAME = "cluster_name"
    IS_DECLARED_POSITIVE = "is_declared_positive"
    DATE_DECLARED_POSITIVE = "date_declared_positive"
    NEAREST_FACILITY = "nearest_facility"
    WARD = "ward"
    LOCAL_BODY = "local_body"
    DISTRICT = "district"
    STATE = "state"


class ClaimViewSetTestCase(TestBase, TestClassMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

    def setUp(self) -> None:
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_list_claims(self):
        response = self.client.get("/api/v1/hcx/claim/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["results"], list)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedClaimListKeys]
        data = response.json()["results"][0]
        self.assertCountEqual(data.keys(), expected_keys)

        policy_object_keys = [key.value for key in ExpectedPolicyListKeys]
        self.assertCountEqual(data["policy_object"].keys(), policy_object_keys)

        item_keys = [key.value for key in ExpectedItemKeys]
        for item in data["items"]:
            self.assertCountEqual(item.keys(), item_keys)

        # Ensure the data is coming in correctly
        data = response.json()["results"][0]
        self.assertIsInstance(data["id"], str)
        self.assertIsInstance(data["outcome"], str)
        self.assertIsInstance(data["error_text"], str)
        self.assertIsInstance(data["created_date"], str)
        self.assertIsInstance(data["use"], str)

        policy_object = data["policy_object"]
        self.assertIsInstance(policy_object["id"], str)
        self.assertIsInstance(policy_object["created_date"], str)
        self.assertIsInstance(policy_object["modified_date"], str)
        self.assertIsInstance(policy_object["subscriber_id"], str)
        self.assertIsInstance(policy_object["policy_id"], str)
        self.assertIsInstance(policy_object["insurer_id"], str)
        self.assertIsInstance(policy_object["insurer_name"], str)

    def test_retrieve_claim(self):
        response = self.client.get(f"/api/v1/hcx/claim/{self.claim.external_id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only necessary data is being sent and no extra data
        expected_keys = [key.value for key in ExpectedClaimRetrieveKeys]
        data = response.json()
        self.assertCountEqual(data.keys(), expected_keys)

        consultation_object_keys = [key.value for key in ExpectedConsultationKeys]
        self.assertCountEqual(
            data["consultation_object"].keys(), consultation_object_keys
        )

        if data["consultation_object"]["referred_to_object"]:
            reffered_to_object_keys = [key.value for key in ExpectedReferredToKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"].keys(),
                reffered_to_object_keys,
            )

            ward_object_keys = [key.value for key in WardKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"]["ward_object"].keys(),
                ward_object_keys,
            )

            local_body_object_keys = [key.value for key in LocalBodyKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"][
                    "local_body_object"
                ].keys(),
                local_body_object_keys,
            )

            district_object_keys = [key.value for key in DistrictKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"][
                    "district_object"
                ].keys(),
                district_object_keys,
            )

            state_object_keys = [key.value for key in StateKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"][
                    "state_object"
                ].keys(),
                state_object_keys,
            )

            facility_object_keys = [key.value for key in FacilityTypeKeys]
            self.assertCountEqual(
                data["consultation_object"]["referred_to_object"][
                    "facility_type"
                ].keys(),
                facility_object_keys,
            )

        if data["consultation_object"]["last_edited_by"]:
            last_edited_by_keys = [key.value for key in ExpectedLastEditedByKeys]
            self.assertCountEqual(
                data["consultation_object"]["last_edited_by"].keys(),
                last_edited_by_keys,
            )

        if data["consultation_object"]["created_by"]:
            created_by_keys = [key.value for key in ExpectedCreatedByKeys]
            self.assertCountEqual(
                data["consultation_object"]["created_by"].keys(), created_by_keys
            )

        policy_object_keys = [key.value for key in ExpectedPolicyRetrieveKeys]
        self.assertCountEqual(data["policy_object"].keys(), policy_object_keys)

        patient_object_keys = [key.value for key in ExpectedPatientObjectKeys]
        self.assertCountEqual(
            data["policy_object"]["patient_object"].keys(), patient_object_keys
        )

        created_by_keys = [key.value for key in ExpectedCreatedByKeys]
        self.assertCountEqual(data["created_by"].keys(), created_by_keys)

        last_modified_by_keys = [key.value for key in ExpectedLastEditedByKeys]
        self.assertCountEqual(data["last_modified_by"].keys(), last_modified_by_keys)

        item_keys = [key.value for key in ExpectedItemKeys]
        for item in data["items"]:
            self.assertCountEqual(item.keys(), item_keys)
