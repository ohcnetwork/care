import abc
import datetime
from collections import OrderedDict
from typing import Any, Dict
from uuid import uuid4

import dateparser
from django.contrib.gis.geos import Point
from pytz import unicode
from rest_framework import status
from rest_framework.test import APITestCase

from care.facility.models import (
    CATEGORY_CHOICES,
    DISEASE_CHOICES_MAP,
    SYMPTOM_CHOICES,
    Disease,
    DiseaseStatusEnum,
    Facility,
    LocalBody,
    PatientConsultation,
    PatientRegistration,
    User,
)
from care.users.models import District, State
from config.tests.helper import EverythingEquals, mock_equal


class TestBase(APITestCase):
    """
    Base class for tests, handles most of the test setup and tools for setting up data
    """

    maxDiff = None

    @classmethod
    def create_user(cls, district: District, username: str = "user", **kwargs):
        data = {
            "email": f"{username}@somedomain.com",
            "phone_number": "5554446667",
            "age": 30,
            "gender": 2,
            "verified": True,
            "username": username,
            "password": "bar",
            "district": district,
            "user_type": User.TYPE_VALUE_MAP["Staff"],
        }
        data.update(kwargs)
        return User.objects.create_user(**data)

    @classmethod
    def create_super_user(cls, district: District, username: str = "superuser"):
        user = cls.create_user(district=district, username=username, user_type=User.TYPE_VALUE_MAP["DistrictAdmin"],)
        user.is_superuser = True
        user.save()
        return user

    @classmethod
    def create_district(cls, state: State):
        return District.objects.create(state=state, name=f"District{datetime.datetime.now().timestamp()}")

    @classmethod
    def create_state(cls):
        return State.objects.create(name=f"State{datetime.datetime.now().timestamp()}")

    @classmethod
    def create_facility(cls, district: District, user: User = None, **kwargs):
        user = user or cls.user
        data = {
            "name": "Foo",
            "district": district,
            "facility_type": 1,
            "address": "8/88, 1st Cross, 1st Main, Boo Layout",
            "location": Point(24.452545, 49.878248),
            "pincode": 123456,
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
            "created_by": user,
        }
        data.update(kwargs)
        f = Facility(**data)
        f.save()
        return f

    @classmethod
    def create_patient(cls, **kwargs):
        patient_data = cls.get_patient_data().copy()
        patient_data.update(kwargs)

        medical_history = patient_data.pop("medical_history", [])
        district_id = patient_data.pop("district", None)
        state_id = patient_data.pop("state", None)

        patient_data.update(
            {
                "district_id": district_id,
                "state_id": state_id,
                "disease_status": getattr(DiseaseStatusEnum, patient_data["disease_status"]).value,
            }
        )

        patient = PatientRegistration.objects.create(**patient_data)
        diseases = [
            Disease.objects.create(patient=patient, disease=DISEASE_CHOICES_MAP[mh["disease"]], details=mh["details"])
            for mh in medical_history
        ]
        patient.medical_history.set(diseases)

        return patient

    @classmethod
    def get_user_data(cls, district: District = None, user_type: str = None):
        """
        Returns the data to be used for API testing

            Returns:
                dict

            Params:
                district: District
                user_type: str(A valid mapping for the integer types mentioned inside the models)
        """
        district = district or cls.district
        user_type = user_type or User.TYPE_VALUE_MAP["Staff"]

        return {
            "user_type": user_type,
            "district": district,
            "state": district.state,
            "phone_number": "8887776665",
            "gender": 2,
            "age": 30,
            "email": "foo@foobar.com",
            "username": "user",
            "password": "bar",
        }

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
            "address": f"Address {datetime.datetime.now().timestamp}",
            "location": {"latitude": 49.878248, "longitude": 24.452545},
            "pincode": 123456,
            "oxygen_capacity": 10,
            "phone_number": "9998887776",
            "capacity": [],
        }

    @classmethod
    def get_patient_data(cls, district=None, state=None):
        return {
            "name": "Foo",
            "age": 32,
            "date_of_birth": datetime.date(1992, 4, 1),
            "gender": 2,
            "is_medical_worker": True,
            "is_antenatal": False,
            "allergies": "",
            "allow_transfer": True,
            "blood_group": "O+",
            "ongoing_medication": "",
            "date_of_return": datetime.datetime(2020, 4, 1, 15, 30, 00),
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
            "state": (state or cls.state).id,
            "district": (district or cls.district).id,
            "local_body": None,
            "number_of_aged_dependents": 2,
            "number_of_chronic_diseased_dependents": 1,
            "medical_history": [{"disease": "Diabetes", "details": "150 count"}],
            "date_of_receipt_of_information": datetime.datetime(2020, 4, 1, 15, 30, 00),
        }

    @classmethod
    def setUpClass(cls) -> None:
        super(TestBase, cls).setUpClass()
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.user_type = User.TYPE_VALUE_MAP["Staff"]
        cls.user = cls.create_user(cls.district)
        cls.super_user = cls.create_super_user(district=cls.district)
        cls.facility = cls.create_facility(cls.district)
        cls.patient = cls.create_patient()

        cls.user_data = cls.get_user_data(cls.district, cls.user_type)
        cls.facility_data = cls.get_facility_data(cls.district)
        cls.patient_data = cls.get_patient_data(cls.district)

    def setUp(self) -> None:
        self.client.force_login(self.user)

    @abc.abstractmethod
    def get_base_url(self):
        """
        Should return the base url of the testing viewset
        WITHOUT trailing slash

        eg: return "api/v1/facility"
        :return: str
        """
        raise NotImplementedError()

    def get_url(self, entry_id=None, action=None, *args, **kwargs):
        url = self.get_base_url(*args, **kwargs)
        if entry_id is not None:
            url = f"{url}/{entry_id}"
        if action is not None:
            url = f"{url}/{action}"
        return f"{url}/"

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

    @abc.abstractmethod
    def get_list_representation(self, obj) -> dict:
        """
        Returns the dict representation of the obj in list API
        :param obj: Object to be represented
        :return: dict
        """
        raise NotImplementedError()

    @abc.abstractmethod
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
        response.update(self.get_local_body_representation(getattr(obj, "local_body", None)))
        response.update(self.get_district_representation(getattr(obj, "district", None)))
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
                },
            }

    def get_district_representation(self, district: District):
        if district is None:
            return {"district": None, "district_object": None}
        return {
            "district": district.id,
            "district_object": {"id": district.id, "name": district.name, "state": district.state.id,},
        }

    def get_state_representation(self, state: State):
        if state is None:
            return {"state": None, "state_object": None}
        return {"state": state.id, "state_object": {"id": state.id, "name": state.name}}

    def assertDictEqual(self, first: Dict[Any, Any], second: Dict[Any, Any], msg: Any = ...) -> None:
        first_dict = self._convert_to_matchable_types(first.copy())
        second_dict = self._convert_to_matchable_types(second.copy())
        return super(TestBase, self).assertDictEqual(first_dict, second_dict, msg)

    def _convert_to_matchable_types(self, d):
        def dict_to_matching_type(d: dict):
            return {k: to_matching_type(k, v) for k, v in d.items()}

        def to_matching_type(name: str, value):
            if isinstance(value, (OrderedDict, dict)):
                return dict_to_matching_type(dict(value))
            elif isinstance(value, list):
                return [to_matching_type("", v) for v in value]
            elif "date" in name and not isinstance(value, (type(None), EverythingEquals)):
                return_value = value
                if isinstance(value, (str, unicode,)):
                    return_value = dateparser.parse(value)
                return (
                    return_value.astimezone(tz=datetime.timezone.utc)
                    if isinstance(return_value, datetime.datetime)
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
                "facility_type": {"id": facility.facility_type, "name": facility.get_facility_type_display()},
                **self.get_local_body_district_state_representation(facility),
            }

    @classmethod
    def get_consultation_data(cls):
        return {
            "patient": cls.patient,
            "facility": cls.facility,
            "symptoms": [SYMPTOM_CHOICES[0][0], SYMPTOM_CHOICES[1][0]],
            "other_symptoms": "No other symptoms",
            "symptoms_onset_date": datetime.datetime(2020, 4, 7, 15, 30),
            "category": CATEGORY_CHOICES[0][0],
            "examination_details": "examination_details",
            "existing_medication": "existing_medication",
            "prescribed_medication": "prescribed_medication",
            "suggestion": PatientConsultation.SUGGESTION_CHOICES[0][0],
            "referred_to": None,
            "admitted": False,
            "admitted_to": None,
            "admission_date": None,
            "discharge_date": None,
            "consultation_notes": "",
            "course_in_facility": "",
            "discharge_advice": {},
            "prescriptions": {},
            "created_date": mock_equal,
            "modified_date": mock_equal,
        }

    @classmethod
    def create_consultation(cls, patient=None, facility=None, referred_to=None, **kwargs) -> PatientConsultation:
        data = cls.get_consultation_data()
        kwargs.update(
            {"patient": patient or cls.patient, "facility": facility or cls.facility, "referred_to": referred_to}
        )
        data.update(kwargs)
        return PatientConsultation.objects.create(**data)
