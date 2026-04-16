import datetime
from secrets import choice

import phonenumbers
from django.urls import reverse
from phonenumbers import PhoneNumberFormat, PhoneNumberType
from rest_framework import status

from care.emr.locks.billing import PatientCreateLock
from care.emr.models.patient import (
    PatientIdentifier,
    PatientIdentifierConfig,
    PatientUser,
)
from care.emr.models.tag_config import TagConfig
from care.emr.resources.patient.spec import BloodGroupChoices, GenderChoices
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase
from care.utils.time_util import care_now


def generate_random_valid_phone_number() -> str:
    regions = ["US", "IN", "GB", "DE", "FR", "JP", "AU", "CA"]
    random_region = choice(regions)
    example_number = phonenumbers.example_number_for_type(
        random_region, PhoneNumberType.MOBILE
    )
    if example_number:
        return phonenumbers.format_number(example_number, PhoneNumberFormat.E164)
    raise ValueError("Unable to generate a valid phone number")


class TestPatientViewSet(CareAPITestBase):
    """
    Test cases for checking Patient CRUD operations

    Tests check if:
    1. Permissions are enforced for all operations
    2. Data validations work
    3. Proper responses are returned
    4. Filters work as expected
    """

    def setUp(self):
        """Set up test data that's needed for all tests"""
        super().setUp()  # Call parent's setUp to ensure proper initialization
        self.base_url = reverse("patient-list")

    def generate_patient_data(self, geo_organization, **kwargs):
        data = {
            "name": self.fake.name(),
            "gender": choice(list(GenderChoices)),
            "address": self.fake.address(),
            "permanent_address": self.fake.address(),
            "pincode": self.fake.random_int(min=100000, max=999999),
            "blood_group": choice(list(BloodGroupChoices)),
            "phone_number": generate_random_valid_phone_number(),
            "emergency_phone_number": generate_random_valid_phone_number(),
            "geo_organization": geo_organization,
        }
        if "age" not in kwargs and "date_of_birth" not in kwargs:
            kwargs["age"] = self.fake.random_int(min=1, max=100)
        data.update(**kwargs)
        return data

    def test_create_patient_unauthenticated(self):
        """Test that unauthenticated users cannot create patients"""
        response = self.client.post(self.base_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_empty_patient_validation(self):
        """Test validation when creating patient with empty data"""
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.post(self.base_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_patient_authorization(self):
        """Test patient creation with proper authorization"""
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(organization, user, role)
        self.client.force_authenticate(user=user)
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_patient_unauthorization(self):
        """Test patient creation with proper authorization"""
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_list_patients.name]
        )
        self.attach_role_organization_user(organization, user, role)
        self.client.force_authenticate(user=user)
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_patient_with_invalid_phone_number(self):
        """Test patient creation with invalid phone number"""
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        invalid_phone_numbers = ["12345", "abcdef", "+1234567890123456", ""]

        organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(organization, user, role)
        self.client.force_authenticate(user=user)

        for invalid_number in invalid_phone_numbers:
            patient_data = self.generate_patient_data(
                geo_organization=geo_organization.external_id,
                phone_number=invalid_number,
            )
            response = self.client.post(self.base_url, patient_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_patient_with_valid_phone_number(self):
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        valid_phone_numbers = [generate_random_valid_phone_number() for _ in range(5)]

        organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(organization, user, role)
        self.client.force_authenticate(user=user)

        for valid_number in valid_phone_numbers:
            patient_data = self.generate_patient_data(
                geo_organization=geo_organization.external_id, phone_number=valid_number
            )
            PatientCreateLock().release()
            response = self.client.post(self.base_url, patient_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_patient_age_and_date_of_birth(self):
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_create_patient.name,
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id,
            date_of_birth=datetime.date(1993, 1, 10),
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date_of_birth"], "1993-01-10")
        self.assertEqual(response.data["year_of_birth"], 1993)
        patient_id = response.data["id"]
        reverse_url = reverse("patient-detail", kwargs={"external_id": patient_id})
        patient_data["age"] = 33
        response = self.client.put(reverse_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date_of_birth"], None)
        self.assertEqual(
            response.data["year_of_birth"],
            datetime.datetime.now(datetime.UTC).year - 33,
        )
        patient_data["date_of_birth"] = datetime.date(1992, 1, 10)
        del patient_data["age"]
        response = self.client.put(reverse_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["date_of_birth"], "1992-01-10")
        self.assertEqual(response.data["year_of_birth"], 1992)

    def test_invalid_date_of_birth_and_death_date(self):
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_create_patient.name,
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        current_date = care_now()
        old_date = current_date - datetime.timedelta(days=365)
        older_date = current_date - datetime.timedelta(days=730)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id,
            date_of_birth=old_date.date(),
            deceased_datetime=older_date,
        )
        response = self.client.post(self.base_url, patient_data, format="json")
        data = response.json()
        status_code = response.status_code
        self.assertEqual(status_code, 400)
        self.assertIn("errors", data)
        error = data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Date of birth cannot be after the date of death", error["msg"])

    def test_create_patient_with_future_deceased_datetime(self):
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id,
            deceased_datetime=care_now() + datetime.timedelta(days=10),
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_delete_patient_as_superuser(self):
        superuser = self.create_super_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, superuser, role)
        self.client.force_authenticate(user=superuser)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]
        delete_url = reverse("patient-detail", kwargs={"external_id": patient_id})
        response = self.client.delete(delete_url)
        self.assertIn(response.status_code, [204, 200])

    def test_delete_patient_as_non_superuser(self):
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_create_patient.name,
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]
        delete_url = reverse("patient-detail", kwargs={"external_id": patient_id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_create_patient.name,
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id,
            deceased_datetime=care_now() - datetime.timedelta(days=2),
            date_of_birth=(care_now() + datetime.timedelta(days=5)).date().isoformat(),
        )
        response = self.client.post(self.base_url, patient_data, format="json")
        data = response.json()
        status_code = response.status_code
        self.assertEqual(status_code, 400)
        self.assertIn("errors", data)
        error = data["errors"][0]
        self.assertEqual(error["type"], "validation_error")
        self.assertIn("Date of birth cannot be after the date of death", error["msg"])

    def _create_patient_with_phone(self, phone_number):
        """Helper to create a patient via API and return the response data"""
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id,
            phone_number=phone_number,
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data, user, geo_organization

    def test_search_by_phone_number(self):
        phone = generate_random_valid_phone_number()
        patient_data, _, _ = self._create_patient_with_phone(phone)
        search_url = reverse("patient-search")
        response = self.client.post(search_url, {"phone_number": phone}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["partial"])
        results = response.data["results"]
        self.assertGreaterEqual(len(results), 1)
        partial_ids = [r["partial_id"] for r in results]
        self.assertIn(str(patient_data["id"])[:5], partial_ids)

    def test_search_without_phone_or_config(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        search_url = reverse("patient-search")
        response = self.client.post(search_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_by_config_without_value(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        config = PatientIdentifierConfig.objects.create(
            status="active",
            config={
                "use": "official",
                "system": "test",
                "required": False,
                "unique": False,
                "regex": "",
                "display": "Test",
            },
        )
        search_url = reverse("patient-search")
        response = self.client.post(
            search_url,
            {"config": str(config.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_retrieve_success(self):
        phone = generate_random_valid_phone_number()
        patient_data, _, _ = self._create_patient_with_phone(phone)
        patient_id = patient_data["id"]
        partial_id = str(patient_id)[:5]
        year_of_birth = patient_data["year_of_birth"]

        search_retrieve_url = reverse("patient-search-retrieve")
        response = self.client.post(
            search_retrieve_url,
            {
                "phone_number": phone,
                "year_of_birth": year_of_birth,
                "partial_id": partial_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], patient_id)

    def test_search_retrieve_no_match(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        search_retrieve_url = reverse("patient-search-retrieve")
        response = self.client.post(
            search_retrieve_url,
            {
                "phone_number": "+19876543210",
                "year_of_birth": 1900,
                "partial_id": "xxxxx",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def _setup_patient_with_write_permission(self):
        """Helper to create a patient and user with write permissions"""
        user = self.create_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_create_patient.name,
                PatientPermissions.can_write_patient.name,
                PatientPermissions.can_list_patients.name,
            ]
        )
        self.attach_role_organization_user(geo_organization, user, role)
        self.client.force_authenticate(user=user)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["id"], user, role, geo_organization

    def test_add_user_to_patient(self):
        patient_id, _, role, _ = self._setup_patient_with_write_permission()
        other_user = self.create_user()
        url = reverse("patient-add-user", kwargs={"external_id": patient_id})
        response = self.client.post(
            url,
            {"user": str(other_user.external_id), "role": str(role.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PatientUser.objects.filter(
                user=other_user, patient__external_id=patient_id
            ).exists()
        )

    def test_add_duplicate_user_to_patient(self):
        patient_id, _, role, _ = self._setup_patient_with_write_permission()
        other_user = self.create_user()
        url = reverse("patient-add-user", kwargs={"external_id": patient_id})
        self.client.post(
            url,
            {"user": str(other_user.external_id), "role": str(role.external_id)},
            format="json",
        )
        response = self.client.post(
            url,
            {"user": str(other_user.external_id), "role": str(role.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_users_for_patient(self):
        patient_id, _, role, _ = self._setup_patient_with_write_permission()
        other_user = self.create_user()
        add_url = reverse("patient-add-user", kwargs={"external_id": patient_id})
        self.client.post(
            add_url,
            {"user": str(other_user.external_id), "role": str(role.external_id)},
            format="json",
        )
        get_url = reverse("patient-get-users", kwargs={"external_id": patient_id})
        response = self.client.get(get_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(other_user.external_id), user_ids)

    def test_delete_user_from_patient(self):
        patient_id, _, role, _ = self._setup_patient_with_write_permission()
        other_user = self.create_user()
        add_url = reverse("patient-add-user", kwargs={"external_id": patient_id})
        self.client.post(
            add_url,
            {"user": str(other_user.external_id), "role": str(role.external_id)},
            format="json",
        )
        self.assertTrue(
            PatientUser.objects.filter(
                user=other_user, patient__external_id=patient_id
            ).exists()
        )
        del_url = reverse("patient-delete-user", kwargs={"external_id": patient_id})
        response = self.client.post(
            del_url,
            {"user": str(other_user.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            PatientUser.objects.filter(
                user=other_user, patient__external_id=patient_id
            ).exists()
        )

    def test_delete_nonexistent_user_from_patient(self):
        patient_id, _, _, _ = self._setup_patient_with_write_permission()
        other_user = self.create_user()
        del_url = reverse("patient-delete-user", kwargs={"external_id": patient_id})
        response = self.client.post(
            del_url,
            {"user": str(other_user.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_appointments(self):
        patient_id, _, _, _ = self._setup_patient_with_write_permission()
        url = reverse("patient-get-appointments", kwargs={"external_id": patient_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_tokens(self):
        patient_id, _, _, _ = self._setup_patient_with_write_permission()
        url = reverse("patient-get-tokens", kwargs={"external_id": patient_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_identifier(self):
        patient_id, _, _, _ = self._setup_patient_with_write_permission()
        config = PatientIdentifierConfig.objects.create(
            status="active",
            config={
                "use": "official",
                "system": "test-id",
                "required": False,
                "unique": False,
                "regex": "",
                "display": "Test Identifier",
            },
        )
        url = reverse("patient-update-identifier", kwargs={"external_id": patient_id})
        response = self.client.post(
            url,
            {"config": str(config.external_id), "value": "ID-12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PatientIdentifier.objects.filter(
                patient__external_id=patient_id, config=config, value="ID-12345"
            ).exists()
        )

    def test_update_identifier_auto_maintained(self):
        patient_id, _, _, _ = self._setup_patient_with_write_permission()
        config = PatientIdentifierConfig.objects.create(
            status="active",
            config={
                "use": "official",
                "system": "auto-id",
                "required": False,
                "unique": False,
                "regex": "",
                "display": "Auto ID",
                "auto_maintained": True,
            },
        )
        url = reverse("patient-update-identifier", kwargs={"external_id": patient_id})
        response = self.client.post(
            url,
            {"config": str(config.external_id), "value": "SHOULD-FAIL"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_instance_tags(self):
        superuser = self.create_super_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, superuser, role)
        self.client.force_authenticate(user=superuser)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]

        tag = TagConfig.objects.create(
            status="active",
            display="Test Tag",
            category="clinical",
            resource="patient",
        )
        url = reverse("patient-set-instance-tags", kwargs={"external_id": patient_id})
        response = self.client.post(
            url, {"tags": [str(tag.external_id)]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag_displays = [t["display"] for t in response.data["instance_tags"]]
        self.assertIn("Test Tag", tag_displays)

    def test_remove_instance_tags(self):
        superuser = self.create_super_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, superuser, role)
        self.client.force_authenticate(user=superuser)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]

        tag = TagConfig.objects.create(
            status="active",
            display="Test Tag",
            category="clinical",
            resource="patient",
        )
        set_url = reverse(
            "patient-set-instance-tags", kwargs={"external_id": patient_id}
        )
        self.client.post(set_url, {"tags": [str(tag.external_id)]}, format="json")
        remove_url = reverse(
            "patient-remove-instance-tags", kwargs={"external_id": patient_id}
        )
        response = self.client.post(
            remove_url, {"tags": [str(tag.external_id)]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["instance_tags"], [])

    def test_set_facility_tags(self):
        superuser = self.create_super_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, superuser, role)
        self.client.force_authenticate(user=superuser)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]

        facility = self.create_facility(user=superuser)
        tag = TagConfig.objects.create(
            facility=facility,
            status="active",
            display="Facility Tag",
            category="clinical",
            resource="patient",
        )
        url = reverse("patient-set-facility-tags", kwargs={"external_id": patient_id})
        response = self.client.post(
            url,
            {
                "tags": [str(tag.external_id)],
                "facility": str(facility.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag_displays = [t["display"] for t in response.data["facility_tags"]]
        self.assertIn("Facility Tag", tag_displays)

    def test_remove_facility_tags(self):
        superuser = self.create_super_user()
        geo_organization = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_create_patient.name]
        )
        self.attach_role_organization_user(geo_organization, superuser, role)
        self.client.force_authenticate(user=superuser)
        patient_data = self.generate_patient_data(
            geo_organization=geo_organization.external_id
        )
        PatientCreateLock().release()
        response = self.client.post(self.base_url, patient_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        patient_id = response.data["id"]

        facility = self.create_facility(user=superuser)
        tag = TagConfig.objects.create(
            facility=facility,
            status="active",
            display="Facility Tag",
            category="clinical",
            resource="patient",
        )
        set_url = reverse(
            "patient-set-facility-tags", kwargs={"external_id": patient_id}
        )
        self.client.post(
            set_url,
            {
                "tags": [str(tag.external_id)],
                "facility": str(facility.external_id),
            },
            format="json",
        )
        remove_url = reverse(
            "patient-remove-facility-tags", kwargs={"external_id": patient_id}
        )
        response = self.client.post(
            remove_url,
            {
                "tags": [str(tag.external_id)],
                "facility": str(facility.external_id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["facility_tags"], [])
