from copy import deepcopy

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from pydantic import ValidationError

from care.emr.resources.user.spec import PublicUserReadSpec, UserSpec, UserUpdateSpec
from care.users.models import User
from care.utils.tests.base import CareAPITestBase

LANGUAGE_SYSTEM = "urn:iso:std:iso:639:-3"
DEGREES = [
    {
        "code": "MBBS",
        "system": "https://example.org/degrees",
        "display": "Bachelor of Medicine and Bachelor of Surgery",
    },
    {
        "code": "MD",
        "system": "https://example.org/degrees",
        "display": "Doctor of Medicine",
    },
]


def profile_data():
    return {
        "communication": [
            {
                "language": {"code": "eng", "system": LANGUAGE_SYSTEM},
                "preferred": True,
                "proficiency": "C1",
            },
            {
                "language": {"code": "mal", "system": LANGUAGE_SYSTEM},
                "preferred": False,
                "proficiency": "B2",
            },
        ],
        "qualification": [
            {
                "registration_number": "REG-1234",
                "issuer": "State Medical Council",
                "degree": {"code": "MBBS", "system": DEGREES[0]["system"]},
                "meta": {
                    "credentialing_plug": {
                        "verified": True,
                        "score": 0.75,
                        "attempts": 2,
                        "notes": None,
                        "evidence": [{"labels": ["primary", "manual"]}],
                        "degree": {"code": "plug-specific", "system": ""},
                    }
                },
            }
        ],
    }


@override_settings(USER_QUALIFICATION_DEGREES=DEGREES)
class UserProfileSpecTestCase(SimpleTestCase):
    def setUp(self):
        self.user_data = {
            "first_name": "Test",
            "last_name": "User",
            "phone_number": "1234567890",
            "gender": "non_binary",
        }

    def test_accepts_iso_639_3_languages(self):
        for code in ["eng", "mal", "hin", "tam", "fra", "deu"]:
            with self.subTest(code=code):
                data = profile_data()
                data["communication"][0]["language"]["code"] = code
                spec = UserUpdateSpec(**self.user_data, **data)
                self.assertEqual(spec.communication[0].language.code, code)

    def test_rejects_invalid_or_non_iso_639_3_language_codes(self):
        for code in ["en", "ger", "xxx", "ENG", " eng", "eng-US"]:
            with self.subTest(code=code):
                data = profile_data()
                data["communication"][0]["language"]["code"] = code
                with self.assertRaises(ValidationError):
                    UserUpdateSpec(**self.user_data, **data)

    def test_rejects_other_language_systems(self):
        data = profile_data()
        data["communication"][0]["language"]["system"] = "urn:ietf:bcp:47"
        with self.assertRaises(ValidationError):
            UserUpdateSpec(**self.user_data, **data)

    def test_accepts_and_serializes_cefr_proficiency_levels(self):
        for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            with self.subTest(level=level):
                data = profile_data()
                data["communication"][0]["proficiency"] = level
                spec = UserUpdateSpec(**self.user_data, **data)
                self.assertEqual(spec.communication[0].proficiency.value, level)
                user = spec.de_serialize(User())
                self.assertEqual(user.communication, data["communication"])
                self.assertIs(type(user.communication[0]["proficiency"]), str)

    def test_rejects_invalid_cefr_proficiency_levels(self):
        for level in ["A0", "A3", "B3", "C3", "a1", "native", "", 1, True]:
            with self.subTest(level=level):
                data = profile_data()
                data["communication"][0]["proficiency"] = level
                with self.assertRaises(ValidationError):
                    UserUpdateSpec(**self.user_data, **data)

    def test_accepts_legacy_communication_without_proficiency(self):
        data = profile_data()
        for communication in data["communication"]:
            del communication["proficiency"]
        spec = UserUpdateSpec(**self.user_data, **data)
        self.assertTrue(
            all(
                communication.proficiency is None
                for communication in spec.communication
            )
        )

        data["communication"][0]["proficiency"] = None
        spec = UserUpdateSpec(**self.user_data, **data)
        self.assertIsNone(spec.communication[0].proficiency)

    def test_rejects_unavailable_degrees_and_mismatched_systems(self):
        for degree in [
            {"code": "UNKNOWN", "system": DEGREES[0]["system"]},
            {"code": "MBBS", "system": "https://example.org/other-degrees"},
        ]:
            with self.subTest(degree=degree):
                data = profile_data()
                data["qualification"][0]["degree"] = degree
                with self.assertRaises(ValidationError):
                    UserUpdateSpec(**self.user_data, **data)

    def test_uses_runtime_degree_configuration(self):
        custom_degree = {"code": "CUSTOM", "system": "https://example.org/custom"}
        data = profile_data()
        data["qualification"][0]["degree"] = custom_degree
        with self.settings(USER_QUALIFICATION_DEGREES=[custom_degree]):
            spec = UserUpdateSpec(**self.user_data, **data)
        self.assertEqual(spec.qualification[0].degree.model_dump(), custom_degree)

    def test_qualification_requires_registration_issuer_and_degree(self):
        for field in ["registration_number", "issuer", "degree"]:
            with self.subTest(field=field):
                data = profile_data()
                del data["qualification"][0][field]
                with self.assertRaises(ValidationError):
                    UserUpdateSpec(**self.user_data, **data)

    def test_qualification_meta_survives_validation_and_serialization(self):
        data = profile_data()
        spec = UserUpdateSpec(**self.user_data, **data)
        user = spec.de_serialize(User(cached_role_orgs={}))
        self.assertEqual(user.qualifications, data["qualification"])

        serialized_user = UserSpec.serialize(user).to_json()
        self.assertEqual(serialized_user["qualification"], data["qualification"])
        self.assertNotIn("meta", serialized_user)

    def test_legacy_qualification_meta_defaults_to_independent_empty_objects(self):
        data = profile_data()
        del data["qualification"][0]["meta"]
        first_spec = UserUpdateSpec(**self.user_data, **data)
        second_spec = UserUpdateSpec(**self.user_data, **data)
        self.assertEqual(first_spec.qualification[0].meta, {})
        self.assertEqual(first_spec.de_serialize(User()).qualifications[0]["meta"], {})

        first_spec.qualification[0].meta["plug"] = {"verified": True}
        self.assertEqual(second_spec.qualification[0].meta, {})

    def test_explicit_empty_arrays_clear_existing_profile(self):
        data = profile_data()
        user = User(
            qualifications=data["qualification"], communication=data["communication"]
        )
        spec = UserUpdateSpec(**self.user_data, qualification=[], communication=[])
        updated_user = spec.de_serialize(user)
        self.assertEqual(updated_user.qualifications, [])
        self.assertEqual(updated_user.communication, [])

    def test_omitted_arrays_preserve_existing_profile(self):
        data = profile_data()
        user = User(
            qualifications=deepcopy(data["qualification"]),
            communication=deepcopy(data["communication"]),
        )
        updated_user = UserUpdateSpec(**self.user_data).de_serialize(user)
        self.assertEqual(updated_user.qualifications, data["qualification"])
        self.assertEqual(updated_user.communication, data["communication"])

    def test_public_profile_does_not_expose_communication_or_qualifications(self):
        data = profile_data()
        user = User(
            qualifications=data["qualification"],
            communication=data["communication"],
            cached_role_orgs={},
        )
        serialized_user = PublicUserReadSpec.serialize(user).to_json()
        self.assertNotIn("communication", serialized_user)
        self.assertNotIn("qualification", serialized_user)
        self.assertNotIn("qualifications", serialized_user)


@override_settings(USER_QUALIFICATION_DEGREES=DEGREES)
class UserProfileAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.super_user = self.create_super_user(username="profileadmin")
        self.user = self.create_user(
            username="profileuser",
            first_name="Profile",
            last_name="User",
            phone_number="1234432100",
            gender="non_binary",
            qualifications=profile_data()["qualification"],
            communication=profile_data()["communication"],
        )
        self.url = reverse("users-detail", kwargs={"username": self.user.username})
        self.update_data = {
            "first_name": "Updated",
            "last_name": "User",
            "phone_number": self.user.phone_number,
            "gender": self.user.gender,
        }

    def test_create_and_retrieve_user_profile(self):
        self.client.force_authenticate(user=self.super_user)
        data = {
            "username": "newprofileuser",
            "first_name": "New",
            "last_name": "User",
            "email": "profile@example.com",
            "password": "ComplexP@ssw0rd",
            "gender": "non_binary",
            "phone_number": "1234567890",
            "role_orgs": [],
            **profile_data(),
        }
        response = self.client.post(reverse("users-list"), data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        created_user = User.objects.get(username=data["username"])
        self.assertEqual(created_user.communication, data["communication"])
        self.assertEqual(created_user.qualifications, data["qualification"])
        response = self.client.get(
            reverse("users-detail", kwargs={"username": created_user.username})
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["communication"], data["communication"])
        self.assertEqual(response.data["qualification"], data["qualification"])

    def test_update_preserves_profile_when_arrays_are_omitted(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.url, self.update_data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.communication, profile_data()["communication"])
        self.assertEqual(self.user.qualifications, profile_data()["qualification"])

    def test_update_replaces_and_clears_profile(self):
        self.client.force_authenticate(user=self.user)
        data = profile_data()
        data["communication"] = [data["communication"][1]]
        data["qualification"][0]["degree"]["code"] = "MD"
        response = self.client.put(
            self.url, {**self.update_data, **data}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.communication, data["communication"])
        self.assertEqual(self.user.qualifications, data["qualification"])

        response = self.client.put(
            self.url,
            {**self.update_data, "communication": [], "qualification": []},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.communication, [])
        self.assertEqual(self.user.qualifications, [])
        self.assertEqual(response.data["communication"], [])
        self.assertEqual(response.data["qualification"], [])

    def test_invalid_profile_update_does_not_modify_user(self):
        self.client.force_authenticate(user=self.user)
        invalid_profiles = []
        data = profile_data()
        data["communication"][0]["language"]["code"] = "en"
        invalid_profiles.append(data)
        data = profile_data()
        data["qualification"][0]["degree"]["code"] = "UNKNOWN"
        invalid_profiles.append(data)
        data = profile_data()
        data["communication"][0]["proficiency"] = "C3"
        invalid_profiles.append(data)
        for profile in invalid_profiles:
            with self.subTest(profile=profile):
                response = self.client.put(
                    self.url, {**self.update_data, **profile}, format="json"
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Profile")
                self.assertEqual(
                    self.user.communication, profile_data()["communication"]
                )
                self.assertEqual(
                    self.user.qualifications, profile_data()["qualification"]
                )

    def test_current_user_and_list_include_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("users-getcurrentuser"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["communication"], profile_data()["communication"]
        )
        self.assertEqual(
            response.data["qualification"], profile_data()["qualification"]
        )

        response = self.client.get(
            reverse("users-list"), {"username": self.user.username}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["communication"],
            profile_data()["communication"],
        )
        self.assertEqual(
            response.data["results"][0]["qualification"],
            profile_data()["qualification"],
        )
