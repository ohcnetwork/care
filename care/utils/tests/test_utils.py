import uuid
from collections import OrderedDict
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from django.test import override_settings
from django.utils.timezone import make_aware, now
from pytz import unicode
from rest_framework import status

from care.facility.models import (
    CATEGORY_CHOICES,
    DISEASE_CHOICES_MAP,
    SYMPTOM_CHOICES,
    Ambulance,
    Disease,
    DiseaseStatusEnum,
    Facility,
    LocalBody,
    PatientConsultation,
    PatientExternalTest,
    PatientRegistration,
    User,
    Ward,
)
from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.bed import Bed, ConsultationBed
from care.facility.models.facility import FacilityUser
from care.facility.models.icd11_diagnosis import (
    ConditionVerificationStatus,
    ConsultationDiagnosis,
    ICD11Diagnosis,
)
from care.users.models import District, State


class override_cache(override_settings):
    """
    Overrides the cache settings for the test to use a
    local memory cache instead of the redis cache
    """

    def __init__(self, decorated):
        self.decorated = decorated
        super().__init__(
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": f"care-test-{uuid.uuid4()}",
                }
            },
        )

    def __call__(self) -> Any:
        return super().__call__(self.decorated)


class EverythingEquals:
    def __eq__(self, other):
        return True


mock_equal = EverythingEquals()


def assert_equal_dicts(d1, d2, ignore_keys=[]):
    def check_equal():
        ignored = set(ignore_keys)
        for k1, v1 in d1.items():
            if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
                print(k1, v1, d2[k1])
                return False
        for k2, v2 in d2.items():
            if k2 not in ignored and k2 not in d1:
                print(k2, v2)
                return False
        return True

    return check_equal()


class TestUtils:
    """
    Base class for tests, handles most of the test setup and tools for setting up data
    """

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def get_base_url(self) -> str:
        """
        Should return the base url of the testing viewset
        eg: return "api/v1/facility/"
        """
        raise NotImplementedError()

    @classmethod
    def create_state(cls, **kwargs) -> State:
        data = {"name": f"State{now().timestamp()}"}
        data.update(kwargs)
        return State.objects.create(**data)

    @classmethod
    def create_district(cls, state: State, **kwargs) -> District:
        data = {"state": state, "name": f"District{now().timestamp()}"}
        data.update(**kwargs)
        return District.objects.create(**data)

    @classmethod
    def create_local_body(cls, district: District, **kwargs) -> LocalBody:
        data = {
            "name": f"LocalBody{now().timestamp()}",
            "district": district,
            "body_type": 10,
            "localbody_code": "d123456",
        }
        data.update(kwargs)
        return LocalBody.objects.create(**data)

    @classmethod
    def get_user_data(cls, district: District, user_type: str = None):
        """
        Returns the data to be used for API testing

            Returns:
                dict

            Params:
                district: District
                user_type: str(A valid mapping for the integer types mentioned
                inside the models)
        """

        return {
            "user_type": user_type or User.TYPE_VALUE_MAP["Nurse"],
            "district": district,
            "state": district.state,
            "phone_number": "8887776665",
            "gender": 2,
            "date_of_birth": date(1992, 4, 1),
            "email": "foo@foobar.com",
            "username": "user",
            "password": "bar",
        }

    @classmethod
    def link_user_with_facility(cls, user: User, facility: Facility, created_by: User):
        FacilityUser.objects.create(user=user, facility=facility, created_by=created_by)

    @classmethod
    def create_user(
        cls,
        username: str = None,
        district: District = None,
        local_body: LocalBody = None,
        **kwargs,
    ) -> User:
        if username is None:
            username = f"user{now().timestamp()}"

        data = {
            "email": f"{username}@somedomain.com",
            "phone_number": "5554446667",
            "date_of_birth": date(1992, 4, 1),
            "gender": 2,
            "verified": True,
            "username": username,
            "password": "bar",
            "state": district.state,
            "district": district,
            "local_body": local_body,
            "user_type": User.TYPE_VALUE_MAP["Nurse"],
        }
        data.update(kwargs)
        user = User.objects.create_user(**data)
        if home_facility := kwargs.get("home_facility"):
            cls.link_user_with_facility(user, home_facility, user)
        return user

    @classmethod
    def create_ward(cls, local_body, **kwargs) -> Ward:
        data = {
            "name": f"Ward{now().timestamp()}",
            "local_body": local_body,
            "number": 1,
        }
        data.update(kwargs)
        return Ward.objects.create(**data)

    @classmethod
    def create_super_user(cls, *args, **kwargs) -> User:
        return cls.create_user(
            *args,
            is_superuser=True,
            user_type=User.TYPE_VALUE_MAP["StateAdmin"],
            **kwargs,
        )

    @classmethod
    def get_facility_data(cls, district):
        """
        Returns the data to be used for API testing

            Returns:
                dict

            Params:
                district: int
                    An id for the instance of District object created
                user_type: str
                    A valid mapping for the integer types mentioned inside the models
        """
        return {
            "name": "Foo",
            "district": (district or cls.district).id,
            "facility_type": 1,
            "address": f"Address {now().timestamp}",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "pincode": 123456,
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
            "capacity": [],
        }

    @classmethod
    def create_facility(
        cls, user: User, district: District, local_body: LocalBody, **kwargs
    ) -> Facility:
        data = {
            "name": "Foo",
            "district": district,
            "state": district.state,
            "local_body": local_body,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "pincode": 123456,
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
            "created_by": user,
        }
        data.update(kwargs)
        facility = Facility.objects.create(**data)
        return facility

    @classmethod
    def get_patient_data(cls, district, state) -> dict:
        return {
            "name": "Foo",
            "date_of_birth": date(1992, 4, 1),
            "gender": 2,
            "is_medical_worker": True,
            "is_antenatal": False,
            "allergies": "",
            "allow_transfer": True,
            "blood_group": "O+",
            "ongoing_medication": "",
            "date_of_return": make_aware(datetime(2020, 4, 1, 15, 30, 00)),
            "disease_status": "SUSPECTED",
            "phone_number": "+918888888888",
            "address": "Global citizen",
            "contact_with_confirmed_carrier": True,
            "contact_with_suspected_carrier": True,
            "estimated_contact_date": None,
            "past_travel": False,
            "countries_travelled": ["Italy"],
            "present_health": "Fine",
            "has_SARI": False,
            "is_active": True,
            "state_id": state.id,
            "district_id": district.id,
            "local_body": None,
            "number_of_aged_dependents": 2,
            "number_of_chronic_diseased_dependents": 1,
            "medical_history": [{"disease": "Diabetes", "details": "150 count"}],
            "date_of_receipt_of_information": make_aware(
                datetime(2020, 4, 1, 15, 30, 00)
            ),
        }

    @classmethod
    def create_patient(cls, district: District, facility: Facility, **kwargs):
        patient_data = cls.get_patient_data(district, district.state).copy()
        medical_history = patient_data.pop("medical_history", [])

        patient_data.update(
            {
                "facility": facility,
                "disease_status": getattr(
                    DiseaseStatusEnum, patient_data["disease_status"]
                ).value,
            }
        )

        patient_data.update(kwargs)
        patient = PatientRegistration.objects.create(**patient_data)
        diseases = [
            Disease.objects.create(
                patient=patient,
                disease=DISEASE_CHOICES_MAP[mh["disease"]],
                details=mh["details"],
            )
            for mh in medical_history
        ]
        patient.medical_history.set(diseases)

        return patient

    @classmethod
    def get_consultation_data(cls):
        return {
            "patient": cls.patient,
            "facility": cls.facility,
            "symptoms": [SYMPTOM_CHOICES[0][0], SYMPTOM_CHOICES[1][0]],
            "other_symptoms": "No other symptoms",
            "symptoms_onset_date": make_aware(datetime(2020, 4, 7, 15, 30)),
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "history_of_present_illness": "history_of_present_illness",
            "treatment_plan": "treatment_plan",
            "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][
                0
            ],  # HOME ISOLATION
            "referred_to": None,
            "encounter_date": make_aware(datetime(2020, 4, 7, 15, 30)),
            "discharge_date": None,
            "consultation_notes": "",
            "course_in_facility": "",
            "created_date": mock_equal,
            "modified_date": mock_equal,
            "patient_no": int(datetime.now().timestamp() * 1000),
        }

    @classmethod
    def create_consultation(
        cls,
        patient: PatientRegistration,
        facility: Facility,
        referred_to=None,
        **kwargs,
    ) -> PatientConsultation:
        data = cls.get_consultation_data().copy()
        kwargs.update(
            {
                "patient": patient,
                "facility": facility,
                "referred_to": referred_to,
            }
        )
        data.update(kwargs)
        consultation = PatientConsultation.objects.create(**data)
        patient.last_consultation = consultation
        patient.facility = consultation.facility
        patient.save()
        return consultation

    @classmethod
    def get_patient_external_test_data(cls, district, local_body, ward) -> dict:
        return {
            "district": district,
            "srf_id": "00/EKM/0000",
            "name": now().timestamp(),
            "age": 24,
            "age_in": "years",
            "gender": "m",
            "mobile_number": 8888888888,
            "address": "Upload test address",
            "ward": ward,
            "local_body": local_body,
            "source": "Secondary contact aparna",
            "sample_collection_date": "2020-10-14",
            "result_date": "2020-10-14",
            "test_type": "Antigen",
            "lab_name": "Karothukuzhi Laboratory",
            "sample_type": "Ag-SD_Biosensor_Standard_Q_COVID-19_Ag_detection_kit",
            "patient_status": "Asymptomatic",
            "is_repeat": True,
            "patient_category": "Cat 17: All individuals who wish to get themselves tested",
            "result": "Negative",
        }

    @classmethod
    def create_patient_external_test(
        cls, district: District, local_body: LocalBody, ward: Ward, **kwargs
    ) -> PatientExternalTest:
        data = cls.get_patient_external_test_data(district, local_body, ward).copy()
        data.update(kwargs)
        return PatientExternalTest.objects.create(**data)

    @classmethod
    def create_asset_location(cls, facility: Facility, **kwargs) -> AssetLocation:
        data = {
            "name": "asset1 location",
            "location_type": 1,
            "facility": facility,
        }
        data.update(kwargs)
        return AssetLocation.objects.create(**data)

    @classmethod
    def create_asset(cls, location: AssetLocation, **kwargs) -> Asset:
        data = {
            "name": "Test Asset",
            "current_location": location,
            "asset_type": 50,
            "warranty_amc_end_of_validity": make_aware(datetime(2030, 4, 1)).date(),
            "qr_code_id": uuid.uuid4(),
        }
        data.update(kwargs)
        return Asset.objects.create(**data)

    @classmethod
    def create_bed(cls, facility: Facility, location: AssetLocation, **kwargs):
        data = {
            "bed_type": 1,
            "description": "Sample bed",
            "facility": facility,
            "location": location,
            "name": "Test Bed",
        }
        data.update(kwargs)
        return Bed.objects.create(**data)

    @classmethod
    def create_consultation_bed(
        cls,
        consultation: PatientConsultation,
        bed: Bed,
        **kwargs,
    ):
        data = {
            "bed": bed,
            "consultation": consultation,
            "start_date": make_aware(datetime(2020, 4, 1, 15, 30)),
        }
        data.update(kwargs)
        return ConsultationBed.objects.create(**data)

    @classmethod
    def create_consultation_diagnosis(
        cls,
        consultation: PatientConsultation,
        diagnosis: ICD11Diagnosis,
        verification_status: ConditionVerificationStatus,
        **kwargs,
    ):
        data = {
            "consultation": consultation,
            "diagnosis": diagnosis,
            "verification_status": verification_status,
        }
        data.update(kwargs)
        return ConsultationDiagnosis.objects.create(**data)

    @classmethod
    def clone_object(cls, obj, save=True):
        new_obj = obj._meta.model.objects.get(pk=obj.id)
        new_obj.pk = None
        new_obj.id = None
        try:
            new_obj.external_id = uuid4()
        except AttributeError:
            pass
        if save:
            new_obj.save()
        return new_obj

    @classmethod
    def get_ambulance_data(cls, district, user) -> dict:
        return {
            "vehicle_number": "KL01AB1234",
            "owner_name": "Foo",
            "owner_phone_number": "9998887776",
            "primary_district": district,
            "has_oxygen": True,
            "has_ventilator": True,
            "has_suction_machine": True,
            "has_defibrillator": True,
            "insurance_valid_till_year": 2021,
            "price_per_km": 10,
            "has_free_service": False,
            "created_by": user,
        }

    @classmethod
    def create_ambulance(cls, district: District, user: User, **kwargs) -> Ambulance:
        data = cls.get_ambulance_data(district, user)
        data.update(**kwargs)
        return Ambulance.objects.create(**data)

    def get_list_representation(self, obj) -> dict:
        """
        Returns the dict representation of the obj in list API
        :param obj: Object to be represented
        :return: dict
        """
        raise NotImplementedError()

    def get_detail_representation(self, obj=None) -> dict:
        """
        Returns the dict representation of the obj in detail/retrieve API
        :param obj: Object to be represented
        :param data: data
        :return: dict
        """
        raise NotImplementedError()

    def get_local_body_district_state_representation(self, obj):
        """
        Returns the local body, district and state representation for the obj.
        The obj is expected to have `local_body`, `district` and `state` in it's attributes
        Eg: Facility, Patient, User

        :param obj: Any object which has `local_body`, `district` and `state` in attrs
        :return:
        """
        response = {}
        response.update(
            self.get_local_body_representation(getattr(obj, "local_body", None))
        )
        response.update(
            self.get_district_representation(getattr(obj, "district", None))
        )
        response.update(self.get_state_representation(getattr(obj, "state", None)))
        return response

    def get_local_body_representation(self, local_body: LocalBody):
        if local_body is None:
            return {"local_body": None, "local_body_object": None}
        else:
            return {
                "local_body": local_body.id,
                "local_body_object": {
                    "id": local_body.id,
                    "name": local_body.name,
                    "district": local_body.district.id,
                    "localbody_code": local_body.localbody_code,
                    "body_type": local_body.body_type,
                },
            }

    def get_district_representation(self, district: District):
        if district is None:
            return {"district": None, "district_object": None}
        return {
            "district": district.id,
            "district_object": {
                "id": district.id,
                "name": district.name,
                "state": district.state.id,
            },
        }

    def get_state_representation(self, state: State):
        if state is None:
            return {"state": None, "state_object": None}
        return {"state": state.id, "state_object": {"id": state.id, "name": state.name}}

    def _convert_to_matchable_types(self, d):
        def dict_to_matching_type(d: dict):
            return {k: to_matching_type(k, v) for k, v in d.items()}

        def to_matching_type(name: str, value):
            if isinstance(value, (OrderedDict, dict)):
                return dict_to_matching_type(dict(value))
            elif isinstance(value, list):
                return [to_matching_type("", v) for v in value]
            elif "date" in name and not isinstance(
                value, (type(None), EverythingEquals)
            ):
                return_value = value
                if isinstance(
                    value,
                    (
                        str,
                        unicode,
                    ),
                ):
                    return_value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
                return (
                    return_value.astimezone(tz=UTC)
                    if isinstance(return_value, datetime)
                    else return_value
                )
            return value

        return dict_to_matching_type(d)

    def execute_list(self, user=None):
        user = user or self.user
        self.client.force_authenticate(user)
        response = self.client.get(self.get_url(), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def get_facility_representation(self, facility):
        if facility is None:
            return facility
        else:
            return {
                "id": str(facility.external_id),
                "name": facility.name,
                "facility_type": {
                    "id": facility.facility_type,
                    "name": facility.get_facility_type_display(),
                },
                **self.get_local_body_district_state_representation(facility),
            }
