from enum import Enum

from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from care.utils.tests.test_base import TestBase


class ExpectedDailyRoundListData(Enum):
    ID = "id"
    TEMPERATURE = "temperature"
    TEMPERATURE_MEASURED_AT = "temperature_measured_at"
    BP = "bp"
    RESP = "resp"
    SPO2 = "spo2"
    VENTILATOR_SPO2 = "ventilator_spo2"
    PULSE = "pulse"
    CREATED_DATE = "created_date"
    ROUNDS_TYPE = "rounds_type"
    PATIENT_CATEGORY = "patient_category"
    PHYSICAL_EXAMINATION_INFO = "physical_examination_info"
    OTHER_DETAILS = "other_details"
    LAST_EDITED_BY = "last_edited_by"
    CREATED_BY = "created_by"
    CREATED_BY_TELEMEDICINE = "created_by_telemedicine"
    LAST_UPDATED_BY_TELEMEDICINE = "last_updated_by_telemedicine"


class ExpectedDailyRoundCreatedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"


class ExpectedDailyRoundLastEditedByKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"


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


class UserBaseMinimumKeys(Enum):
    ID = "id"
    FIRST_NAME = "first_name"
    USERNAME = "username"
    EMAIL = "email"
    LAST_NAME = "last_name"
    USER_TYPE = "user_type"
    LAST_LOGIN = "last_login"


class TestDailyRoundApi(TestBase):
    analyse_url = "/api/v1/consultation/{}/daily_rounds/analyse/"
    daily_rounds_url = "/api/v1/consultation/{}/daily_rounds/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

        cls.consultation = cls.create_consultation()

        # create daily round
        cls.daily_round = cls.create_daily_round(consultation=cls.consultation)

    def setUp(self):
        refresh_token = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

    def test_external_consultation_does_not_exists_returns_404(self):
        external_consultation_id = "e4a3d84a-d678-4992-9287-114f029046d8"
        response = self.client.get(self.analyse_url.format(external_consultation_id))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_daily_rounds_list(self):
        response = self.client.get(
            self.daily_rounds_url.format(self.consultation.external_id)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        results = data["results"]
        self.assertIsInstance(results, list)

        for result in results:
            self.assertCountEqual(
                result.keys(),
                [item.value for item in ExpectedDailyRoundListData],
            )

        created_by_content = result["created_by"]

        if created_by_content is not None:
            self.assertCountEqual(
                created_by_content.keys(),
                [item.value for item in UserBaseMinimumKeys],
            )

        last_edited_by = result["last_edited_by"]

        if last_edited_by is not None:
            self.assertCountEqual(
                last_edited_by.keys(),
                [item.value for item in UserBaseMinimumKeys],
            )

    def test_daily_rounds_retrieve(self):
        response = self.client.get(
            self.daily_rounds_url.format(self.consultation.external_id)
            + str(self.daily_round.external_id)
            + "/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertCountEqual(
            data.keys(),
            [item.value for item in ExpectedDailyRoundRetrieveData],
        )

        created_by_content = data["created_by"]

        if created_by_content is not None:
            self.assertCountEqual(
                created_by_content.keys(),
                [item.value for item in UserBaseMinimumKeys],
            )

        last_edited_by = data["last_edited_by"]

        if last_edited_by is not None:
            self.assertCountEqual(
                last_edited_by.keys(),
                [item.value for item in UserBaseMinimumKeys],
            )
