import uuid
from collections import OrderedDict
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from django.test import override_settings
from django.utils.timezone import make_aware, now
from faker import Faker
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from care.facility.models import (
    BREATHLESSNESS_CHOICES,
    CATEGORY_CHOICES,
    DISEASE_CHOICES_MAP,
    FACILITY_TYPES,
    SHIFTING_STATUS_CHOICES,
    VEHICLE_CHOICES,
    Ambulance,
    Disease,
    DiseaseStatusEnum,
    EncounterSymptom,
    Facility,
    InvestigationSession,
    InvestigationValue,
    LocalBody,
    PatientConsultation,
    PatientExternalTest,
    PatientInvestigation,
    PatientInvestigationGroup,
    PatientRegistration,
    PatientSample,
    Prescription,
    ShiftingRequest,
    ShiftingRequestComment,
    User,
    Ward,
)
from care.facility.models.asset import Asset, AssetLocation
from care.facility.models.bed import AssetBed, Bed, ConsultationBed
from care.facility.models.facility import FacilityUser
from care.facility.models.icd11_diagnosis import (
    ConditionVerificationStatus,
    ConsultationDiagnosis,
    ICD11Diagnosis,
)
from care.facility.models.patient import RationCardCategory
from care.facility.models.patient_consultation import (
    ConsentType,
    PatientCodeStatusType,
    PatientConsent,
)
from care.users.models import District, State

fake = Faker()


class OverrideCache(override_settings):
    """
    Overrides the cache settings for the test to use a
    local memory cache instead of the redis cache
    """

    def __init__(self, decorated):
        self.decorated = decorated
        super().__init__(
            CACHES={
                "default": {
                    "BACKEND": "config.caches.LocMemCache",
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


def assert_equal_dicts(d1, d2, ignore_keys=None):
    if ignore_keys is None:
        ignore_keys = []

    def check_equal():
        ignored = set(ignore_keys)
        for k1, v1 in d1.items():
            if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
                print(k1, v1, d2[k1])  # noqa: T201
                return False
        for k2, v2 in d2.items():
            if k2 not in ignored and k2 not in d1:
                print(k2, v2)  # noqa: T201
                return False
        return True

    return check_equal()


class TestUtils:
    """
    Base class for tests, handles most of the test setup and tools for setting up data
    """

    maxDiff = None

    def setUp(self) -> None:
        self.client.force_login(self.user)

    def get_base_url(self) -> str:
        """
        Should return the base url of the testing viewset
        eg: return "api/v1/facility/"
        """
        raise NotImplementedError

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
    def get_user_data(cls, district: District, user_type: str | None = None):
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
        username: str | None = None,
        district: District = None,
        local_body: LocalBody = None,
        **kwargs,
    ) -> User:
        if username is None:
            username = f"user{now().timestamp()}"

        data = {
            "first_name": "Foo",
            "last_name": "Bar",
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
        return Facility.objects.create(**data)

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
            "ration_card_category": RationCardCategory.NON_CARD_HOLDER,
        }

    @classmethod
    def create_patient(
        cls, district: District, facility: Facility, **kwargs
    ) -> PatientRegistration:
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
    def get_consultation_data(cls) -> dict:
        return {
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "history_of_present_illness": "history_of_present_illness",
            "treatment_plan": "treatment_plan",
            "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][
                0
            ],  # HOME ISOLATION
            "encounter_date": make_aware(datetime(2020, 4, 7, 15, 30)),
            "discharge_date": None,
            "consultation_notes": "",
            "course_in_facility": "",
            "patient_no": int(now().timestamp() * 1000),
            "route_to_facility": 10,
        }

    @classmethod
    def create_consultation(
        cls,
        patient: PatientRegistration,
        facility: Facility,
        doctor: User | None = None,
        referred_to=None,
        **kwargs,
    ) -> PatientConsultation:
        data = cls.get_consultation_data().copy()
        kwargs.update(
            {
                "patient": patient,
                "facility": facility,
                "referred_to": referred_to,
                "treating_physician": doctor,
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
    def create_patient_consent(
        cls,
        consultation: PatientConsultation,
        **kwargs,
    ):
        data = {
            "consultation": consultation,
            "type": ConsentType.PATIENT_CODE_STATUS,
            "patient_code_status": PatientCodeStatusType.COMFORT_CARE,
            "created_by": consultation.created_by,
        }
        data.update(kwargs)
        return PatientConsent.objects.create(**data)

    @classmethod
    def clone_object(cls, obj, save=True):
        new_obj = obj._meta.model.objects.get(pk=obj.id)  # noqa: SLF001
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

    @classmethod
    def get_patient_sample_data(cls, patient, consultation, facility, user) -> dict:
        return {
            "patient": patient,
            "consultation": consultation,
            "sample_type": 1,
            "sample_type_other": "sample sample type other field",
            "has_sari": False,
            "has_ari": False,
            "doctor_name": "Sample Doctor",
            "diagnosis": "Sample diagnosis",
            "diff_diagnosis": "Sample different diagnosis",
            "etiology_identified": "Sample etiology identified",
            "is_atypical_presentation": False,
            "atypical_presentation": "Sample atypical presentation",
            "is_unusual_course": False,
            "icmr_category": 10,
            "icmr_label": "Sample ICMR",
            "date_of_sample": make_aware(datetime(2020, 4, 1, 15, 30, 00)),
            "date_of_result": make_aware(datetime(2020, 4, 5, 15, 30, 00)),
            "testing_facility": facility,
            "created_by": user,
            "last_edited_by": user,
        }

    @classmethod
    def create_patient_sample(
        cls,
        patient: PatientRegistration,
        consultation: PatientConsultation,
        facility: Facility,
        user: User,
        **kwargs,
    ) -> PatientSample:
        data = cls.get_patient_sample_data(patient, consultation, facility, user)
        data.update(**kwargs)
        sample = PatientSample.objects.create(**data)

        # To make date static updating the object here for pdf testing
        sample.created_date = make_aware(datetime(2020, 4, 1, 15, 30, 00))
        sample.save()
        return sample

    @classmethod
    def get_encounter_symptom_data(cls, consultation, user) -> dict:
        return {
            "symptom": 2,
            "onset_date": make_aware(datetime(2020, 4, 1, 15, 30, 00)),
            "cure_date": make_aware(datetime(2020, 5, 1, 15, 30, 00)),
            "clinical_impression_status": 3,
            "consultation": consultation,
            "created_by": user,
            "updated_by": user,
            "is_migrated": False,
        }

    @classmethod
    def create_encounter_symptom(
        cls, consultation: PatientConsultation, user: User, **kwargs
    ) -> EncounterSymptom:
        data = cls.get_encounter_symptom_data(consultation, user)
        data.update(**kwargs)
        return EncounterSymptom.objects.create(**data)

    @classmethod
    def get_patient_investigation_data(cls) -> dict:
        return {
            "name": "Sample Investigation",
            "unit": "mg/dL",
            "ideal_value": "50-100",
            "min_value": 50.0,
            "max_value": 100.0,
            "investigation_type": "Choice",
            "choices": "Option1,Option2,Option3",
        }

    @classmethod
    def create_patient_investigation(
        cls, patient_investigation_group: PatientInvestigationGroup, **kwargs
    ) -> PatientInvestigation:
        data = cls.get_patient_investigation_data()
        data.update(**kwargs)
        investigation = PatientInvestigation.objects.create(**data)
        if "groups" in kwargs:
            investigation.groups.set(kwargs["groups"])
        else:
            investigation.groups.set([patient_investigation_group])
        return investigation

    @classmethod
    def get_patient_investigation_group_data(cls) -> dict:
        return {
            "name": "Sample Investigation group",
        }

    @classmethod
    def create_patient_investigation_group(cls, **kwargs) -> PatientInvestigationGroup:
        data = cls.get_patient_investigation_group_data()
        data.update(**kwargs)
        return PatientInvestigationGroup.objects.create(**data)

    @classmethod
    def get_patient_investigation_session_data(cls, user) -> dict:
        return {
            "created_by": user,
        }

    @classmethod
    def create_patient_investigation_session(
        cls, user: User, **kwargs
    ) -> InvestigationSession:
        data = cls.get_patient_investigation_session_data(user)
        data.update(**kwargs)
        return InvestigationSession.objects.create(**data)

    @classmethod
    def get_investigation_value_data(
        cls, investigation, consultation, session, group
    ) -> dict:
        return {
            "investigation": investigation,
            "group": group,
            "value": 5.0,
            "notes": "Sample notes",
            "consultation": consultation,
            "session": session,
        }

    @classmethod
    def create_investigation_value(
        cls,
        investigation: PatientInvestigation,
        consultation: PatientConsultation,
        session: InvestigationSession,
        group: PatientInvestigationGroup,
        **kwargs,
    ) -> InvestigationValue:
        data = cls.get_investigation_value_data(
            investigation, consultation, session, group
        )
        data.update(**kwargs)
        investigation_value = InvestigationValue.objects.create(**data)
        # To make created date static updating the object here for pdf testing
        investigation_value.created_date = make_aware(datetime(2020, 4, 1, 15, 30, 00))
        investigation_value.save()
        return investigation_value

    @classmethod
    def get_disease_data(cls, patient) -> dict:
        return {
            "patient": patient,
            "disease": 4,
            "details": "Sample disease details",
        }

    @classmethod
    def create_disease(cls, patient: PatientRegistration, **kwargs) -> Disease:
        data = cls.get_disease_data(patient)
        data.update(**kwargs)
        return Disease.objects.create(**data)

    @classmethod
    def get_prescription_data(cls, consultation, user) -> dict:
        return {
            "consultation": consultation,
            "prescription_type": "REGULAR",
            "medicine": None,
            "medicine_old": "Sample old Medicine",
            "route": "Oral",
            "base_dosage": "500mg",
            "dosage_type": "REGULAR",
            "target_dosage": "1000mg",
            "instruction_on_titration": "Sample Instruction for titration",
            "frequency": "8th hourly",
            "days": 7,
            # prn fields
            "indicator": "Sample indicator",
            "max_dosage": "2000mg",
            "min_hours_between_doses": 6,
            "notes": "Take with food",
            "prescribed_by": user,
            "discontinued": False,
            "discontinued_reason": "sample discontinued reason",
            "discontinued_date": date(2020, 4, 1),
        }

    @classmethod
    def create_prescription(
        cls, consultation: PatientConsultation, user: User, **kwargs
    ) -> Prescription:
        data = cls.get_prescription_data(consultation, user)
        data.update(**kwargs)
        return Prescription.objects.create(**data)

    @classmethod
    def create_assetbed(cls, bed: Bed, asset: Asset, **kwargs) -> AssetBed:
        data = {"bed": bed, "asset": asset}
        data.update(kwargs)
        return AssetBed.objects.create(**data)

    def get_list_representation(self, obj) -> dict:
        """
        Returns the dict representation of the obj in list API
        :param obj: Object to be represented
        :return: dict
        """
        raise NotImplementedError

    def get_detail_representation(self, obj=None) -> dict:
        """
        Returns the dict representation of the obj in detail/retrieve API
        :param obj: Object to be represented
        :param data: data
        :return: dict
        """
        raise NotImplementedError

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

    def get_local_body_representation(self, local_body: LocalBody | None):
        if local_body is None:
            return {"local_body": None, "local_body_object": None}
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

    def get_district_representation(self, district: District | None):
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

    def get_state_representation(self, state: State | None):
        if state is None:
            return {"state": None, "state_object": None}
        return {"state": state.id, "state_object": {"id": state.id, "name": state.name}}

    def _convert_to_matchable_types(self, d):
        def dict_to_matching_type(d: dict):
            return {k: to_matching_type(k, v) for k, v in d.items()}

        def to_matching_type(name: str, value):
            if isinstance(value, OrderedDict | dict):
                return dict_to_matching_type(dict(value))
            if isinstance(value, list):
                return [to_matching_type("", v) for v in value]
            if "date" in name and not isinstance(value, type(None) | EverythingEquals):
                return_value = value
                if isinstance(value, str):
                    return_value = datetime.strptime(
                        value, "%Y-%m-%dT%H:%M:%S.%fZ"
                    ).astimezone()
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
        return {
            "id": str(facility.external_id),
            "name": facility.name,
            "facility_type": {
                "id": facility.facility_type,
                "name": facility.get_facility_type_display(),
            },
            **self.get_local_body_district_state_representation(facility),
        }

    def create_patient_note(
        self, patient=None, note="Patient is doing find", created_by=None, **kwargs
    ):
        data = {
            "facility": patient.facility or self.facility,
            "note": note,
        }
        data.update(kwargs)
        patient_id = patient.external_id

        refresh_token = RefreshToken.for_user(created_by)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_token.access_token}"
        )

        self.client.post(f"/api/v1/patient/{patient_id}/notes/", data=data)

    @classmethod
    def create_patient_shift(
        cls,
        facility: Facility = None,
        user: User = None,
        patient: PatientRegistration = None,
        **kwargs,
    ) -> None:
        shifting_approving_facility = cls.create_facility(
            user=cls.user, district=cls.district, local_body=cls.local_body
        )
        assigned_facility = shifting_approving_facility
        data = {
            "origin_facility": assigned_facility,
            "shifting_approving_facility": shifting_approving_facility,
            "assigned_facility_type": fake.random_element(FACILITY_TYPES)[0],
            "assigned_facility": assigned_facility,
            "assigned_facility_external": "Assigned Facility External",
            "patient": patient,
            "emergency": False,
            "is_up_shift": False,
            "reason": "Reason",
            "vehicle_preference": "Vehicle Preference",
            "preferred_vehicle_choice": fake.random_element(VEHICLE_CHOICES)[0],
            "comments": "Comments",
            "refering_facility_contact_name": "9900199001",
            "refering_facility_contact_number": "9900199001",
            "is_kasp": False,
            "status": fake.random_element(SHIFTING_STATUS_CHOICES)[0],
            "breathlessness_level": fake.random_element(BREATHLESSNESS_CHOICES)[0],
            "is_assigned_to_user": False,
            "assigned_to": user,
            "ambulance_driver_name": fake.name(),
            "ambulance_phone_number": "9900199001",
            "ambulance_number": fake.license_plate(),
            "created_by": user,
            "last_edited_by": user,
        }
        data.update(kwargs)
        return ShiftingRequest.objects.create(**data)

    @classmethod
    def create_patient_shift_comment(
        cls, resource: ShiftingRequest = None, user: User = None, **kwargs
    ) -> None:
        kwargs.update(
            {
                "request": resource,
                "comment": "comment",
                "created_by": user,
            }
        )
        return ShiftingRequestComment.objects.create(**kwargs)
