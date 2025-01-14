from secrets import choice

import phonenumbers
from django.urls import reverse
from phonenumbers import PhoneNumberFormat, PhoneNumberType
from rest_framework import status

from care.emr.resources.patient.spec import BloodGroupChoices, GenderChoices
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


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
            response = self.client.post(self.base_url, patient_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
